"""Commands for the revamp: ``live`` (LAN games + lab), ``examine``, and ``forward``.

``examine`` runs ``forensics.examine`` on one evidence file and can write the
Halloween findings page (heatmap, meter, facts, scrub check, tree) as one HTML
file. ``forward`` re-stamps a copy for a new holder and logs the hop, so later
leaks reveal the path.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Annotated

import typer

from molehunt.cli_app import DEFAULT_DB, DEFAULT_KEY, DEFAULT_MASTERS, app, fail, read_employee_ids
from molehunt.cli_app import read_key as _read_key

LIVE_MASTER = DEFAULT_MASTERS / "live" / "m8_midnight_carnival.md"
ROSTER = Path("data/demo/roster50.csv")


def _addresses() -> list[str]:
    found = {info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None,
                                                       socket.AF_INET)}
    return sorted(found - {"127.0.0.1"}) or ["127.0.0.1"]


@app.command()
def live(
    master: Annotated[Path, typer.Option("--master")] = LIVE_MASTER,
    employees: Annotated[Path, typer.Option("--employees", help="Lab roster")] = ROSTER,
    key_file: Annotated[Path, typer.Option("--key-file")] = DEFAULT_KEY,
    db_file: Annotated[Path, typer.Option("--db-file")] = DEFAULT_DB,
    host: Annotated[str, typer.Option("--host", help="0.0.0.0 = all LAN interfaces")]
    = "0.0.0.0",
    port: Annotated[int, typer.Option("--port")] = 8765,
    workdir: Annotated[Path, typer.Option("--workdir")] = Path(".molehunt/live"),
    minutes: Annotated[int, typer.Option("--minutes", help="Escape-room clock")] = 30,
) -> None:
    """LAN party: Find the Mole, Escape Room, and the Forensic Lab on one server."""
    from molehunt.core.keys import load_or_create_key
    from molehunt.game.escape_room import EscapeRoom
    from molehunt.game.mole_game import MoleGame
    from molehunt.live import LiveState, make_server

    try:
        key = load_or_create_key(key_file)
        state = LiveState(master, read_employee_ids(employees), key, db_file, workdir)
        game, room = MoleGame(master, key), EscapeRoom(master, key, duration=minutes * 60)
        urls = tuple(f"http://{address}:{port}/" for address in _addresses())
        server = make_server(state, host, port, game=game, escape=room, join_urls=urls)
    except (OSError, ValueError) as error:
        fail(error)
    typer.echo(f"PIN for players: {state.pin}")
    for url in urls:
        typer.echo(f"Players open:   {url}")
    typer.echo(f"Host console:   http://127.0.0.1:{server.server_port}/host?k={state.host_key}")
    typer.echo("  (open the host link on THIS laptop only; it unlocks the projector screens)")
    typer.echo(f"Seeds (for the log): game {game.seed}, escape {room.seed}")
    typer.echo("Same Wi-Fi only. Allow Python through the firewall if asked. Ctrl+C stops.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("Stopped.")
    finally:
        server.server_close()


@app.command("examine")
def examine_command(
    evidence: Annotated[Path, typer.Argument(help="Evidence file: txt, md, docx, or png")],
    master: Annotated[Path, typer.Option("--master")],
    employees: Annotated[Path, typer.Option("--employees", help="Roster CSV with id column")],
    key_file: Annotated[Path, typer.Option("--key-file")] = DEFAULT_KEY,
    db_file: Annotated[Path, typer.Option("--db-file")] = DEFAULT_DB,
    html: Annotated[Path | None, typer.Option("--html", help="Write the findings page")] = None,
) -> None:
    """Every check on one leak: fingerprint, canary facts, scrub check, family tree."""
    from molehunt.analysis import evidence_text
    from molehunt.core.lineage import ForwardLog
    from molehunt.detect.ingest import ingest
    from molehunt.forensics import examine

    try:
        record = ingest(evidence)
        forwards = ForwardLog(db_file).paths() if db_file.is_file() else []
        found = examine(master.read_text(encoding="utf-8"), _read_key(key_file),
                        read_employee_ids(employees), evidence_text(record), forwards)
    except (OSError, UnicodeError, ValueError) as error:
        fail(error)
    typer.echo(f"Evidence SHA-256: {record.sha256}")
    typer.echo(f"Finding ({found.decision.outcome}): {found.decision.statement}")
    margin = found.curve[-1] if found.curve else 0.0
    typer.echo(f"Meter: {found.leader} vs {found.runner_up}, margin log10 LR {margin:.2f}")
    if found.canaries is not None:
        seen = ", ".join(f"{k}={'/'.join(v)}" for k, v in found.canaries.seen.items()) or "none"
        top = found.canaries.scores[0]
        typer.echo(f"Canary facts seen: {seen}; best match {top.holder} "
                   f"({top.hits} hit, {top.misses} miss)")
    typer.echo(f"Scrub check: {found.scrub.verdict}")
    for signal in found.scrub.signals:
        typer.echo(f"  {'!' if signal.fired else '-'} {signal.reason}")
    typer.echo("Hops: " + " -> ".join(f"{h.holder} ({h.matches}/{h.slots})" for h in found.hops))
    for line in found.tree:
        typer.echo(f"  {line}")
    if html is not None:
        from molehunt.web.findings import METER_SCRIPT, findings_html
        from molehunt.web.theme import page

        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text(page(f"Findings {evidence.name}", findings_html(found),
                             script=METER_SCRIPT, standalone=True), encoding="utf-8")
        typer.echo(f"Findings page: {html}")


@app.command()
def forward(
    sender: Annotated[str, typer.Option("--from", help="Current holder path, e.g. E007")],
    recipient: Annotated[str, typer.Option("--to", help="New holder id, e.g. C12")],
    master_id: Annotated[str, typer.Option("--master", help="Registered master id")],
    output: Annotated[Path, typer.Option("--output", "-o", help=".txt/.docx/.pdf/.png")],
    key_file: Annotated[Path, typer.Option("--key-file")] = DEFAULT_KEY,
    db_file: Annotated[Path, typer.Option("--db-file")] = DEFAULT_DB,
) -> None:
    """Forward a copy: log the hop and issue a re-stamped copy for the recipient."""
    from molehunt.core.lineage import ForwardLog
    from molehunt.issuance import issue_registered_copy

    try:
        child = ForwardLog(db_file).forward(sender, recipient)
        result = issue_registered_copy(db_file, _read_key(key_file), child, master_id, output)
    except (OSError, ValueError) as error:
        fail(error)
    typer.echo(f"Forwarded {sender} -> {recipient}: copy {result.copy_id} for path {child}")
    typer.echo(f"Written: {result.output_path}")
