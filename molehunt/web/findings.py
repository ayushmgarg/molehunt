"""HTML for one examination: verdict, attribution-o-meter, heatmap, facts, scrub, tree.

Shared by the forensic lab, the Find-the-Mole reveal, and the escape room, so all
screens show the same evidence. The meter is an SVG half-dial; a short script walks
the evidence curve (one step per observed slot) and moves the needle, so the room
watches the evidence build up. The needle's full scale is log10 LR margin 10, and
the red tick at 2 is the decision rule's separation threshold.
"""

from __future__ import annotations

import json
from html import escape

from molehunt.detect.decide import verbal_scale
from molehunt.forensics import Examination
from molehunt.web.theme import icon, pill

INVISIBLE = {"zw": "•", "nbsp": "␣"}

_METER_JS = """<script>
(function(){var box=document.getElementById('meter');if(!box)return;
var c=JSON.parse(box.dataset.curve),i=0,n=document.getElementById('needle'),
t=document.getElementById('meterText');
function show(v,k){var a=Math.max(0,Math.min(v,10))/10*180-90;
n.setAttribute('transform','rotate('+a+' 150 150)');
t.textContent='slot '+k+'/'+c.length+'  margin '+v.toFixed(2)+(v>=2?'  ATTRIBUTE':'');}
function step(){if(i<c.length){show(c[i],i+1);i++;setTimeout(step,Math.max(15,2500/c.length));}}
document.querySelectorAll('.heat .reveal').forEach(function(e){e.style.display='inline'});
if(c.length){step()}else{show(0,0)}})();
</script>"""


def _meter(found: Examination) -> str:
    final = found.curve[-1] if found.curve else 0.0
    ticks = "".join(
        f'<line x1="150" y1="40" x2="150" y2="{58 if v % 5 else 66}" '
        f'stroke="{"#ff3b3b" if v == 2 else "#a99bb5"}" stroke-width="{4 if v == 2 else 2}" '
        f'transform="rotate({v * 18 - 90} 150 150)" />' for v in range(11))
    arc = "M30 150 A120 120 0 0 1 270 150"
    return (f"<div id=meter data-curve='{escape(json.dumps(found.curve))}'>"
            '<svg class="gauge" viewBox="0 0 300 180" width="100%" style="max-width:420px">'
            '<defs><linearGradient id="mg"><stop offset="0" stop-color="#7d7590" />'
            '<stop offset=".2" stop-color="#ffd166" /><stop offset="1" stop-color="#7cfc00" />'
            f'</linearGradient></defs><path d="{arc}" fill="none" stroke="#3b2650" '
            f'stroke-width="22" /><path d="{arc}" fill="none" stroke="url(#mg)" '
            f'stroke-width="10" />{ticks}'
            '<line id="needle" x1="150" y1="150" x2="150" y2="48" stroke="#ff7518" '
            'stroke-width="5" stroke-linecap="round" transform="rotate(-90 150 150)" />'
            '<circle cx="150" cy="150" r="10" fill="#ff7518" />'
            '<text id="meterText" x="150" y="176" text-anchor="middle" font-size="13"></text>'
            "</svg>"
            f"<p class=dim>{escape(found.leader)} vs {escape(found.runner_up)}: final margin "
            f"log10 LR {final:.2f} ({escape(verbal_scale(final))}).</p></div>")


def _heat(found: Examination) -> str:
    parts = []
    for segment in found.segments:
        text = escape(segment.text)
        if segment.kind == "plain":
            parts.append(text)
            continue
        marker = INVISIBLE.get(segment.channel, "")
        badge = f"<span class='inv reveal'>{marker}</span>" if marker else ""
        title = f"{segment.channel or 'fact'}: {segment.kind}"
        parts.append(f"<span class={segment.kind} title='{escape(title)}'>{text}{badge}</span>")
    return "<div class='heat copy'>" + "".join(parts) + "</div>"


def _facts(found: Examination) -> str:
    report = found.canaries
    if report is None:
        return "<p class=dim>This master has no canary facts.</p>"
    if not report.seen:
        return "<p class=dim>No canary facts appear in the leak.</p>"
    rows = "".join(f"<tr><td>{escape(name)}</td><td>{escape(', '.join(values))}</td></tr>"
                   for name, values in report.seen.items())
    top = report.scores[0]
    merged = (pill("two values of one fact: copies were merged", "warn")
              if report.merged_families else "")
    return (f"<table>{rows}</table><p>Facts point at <b>{escape(top.holder)}</b> "
            f"({top.hits} of {top.hits + top.misses} facts match, log10 LR {top.log10_lr:.2f}). "
            f"{merged}</p>")


def _scrub(found: Examination) -> str:
    report = found.scrub
    tone = {"deliberately sanitised": "bad", "partly sanitised": "warn"}.get(report.verdict, "good")
    items = "".join(f"<li>{'&#9760; ' if s.fired else ''}{escape(s.reason)}</li>"
                    for s in report.signals)
    return f"<p>{pill(report.verdict, tone)}</p><ul>{items}</ul>"


def _lineage(found: Examination) -> str:
    hops = " &rarr; ".join(
        f"<b>{escape(hop.holder)}</b> <small>({hop.matches}/{hop.slots})</small>"
        for hop in found.hops)
    tree = escape("\n".join(found.tree)) if len(found.tree) > 1 else "No forwards registered."
    return f"<p>Company &rarr; {hops}</p><pre class=copy>{tree}</pre>"


def findings_html(found: Examination, *, title: str = "Forensic findings") -> str:
    """Full findings block (no page wrapper)."""
    decision = found.decision
    tone = "bad" if decision.outcome == "attribute" else "warn"
    ranking = "".join(
        f"<tr><td>{escape(s.candidate_id)}</td><td>{s.matches}/{s.observed_slots}</td>"
        f"<td>{s.log10_lr:.1f}</td></tr>" for s in found.result.scores[:5])
    observed = f"{found.result.observed_slots}/{len(found.result.observations)}"
    return f"""
<div class=card><h2>{icon('fingerprint')}{escape(title)}</h2>
<p>{pill(decision.outcome, tone)} {escape(decision.statement)}</p>{_meter(found)}</div>
<div class=card><h2>{icon('eye')}Heatmap</h2>
<p class=dim>Green = slot matches {escape(found.leader)}, red = mismatch, grey = erased
(missing data), gold = canary fact. {observed} slots readable.</p>{_heat(found)}</div>
<div class=grid>
<div class=card><h2>{icon('search')}Canary facts</h2>{_facts(found)}</div>
<div class=card><h2>{icon('skull')}Scrub check</h2>{_scrub(found)}</div>
</div>
<div class=grid>
<div class=card><h2>{icon('ghost')}Leak family tree</h2>{_lineage(found)}</div>
<div class=card><h2>{icon('trophy')}Ranking</h2><table><tr><th>Copy</th><th>Matches</th>
<th>log10 LR</th></tr>{ranking}</table></div></div>"""


METER_SCRIPT = _METER_JS
