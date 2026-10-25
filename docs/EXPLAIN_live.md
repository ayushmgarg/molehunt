# Explain: live LAN mode (live.py, cli_live.py)

`molehunt live` starts one server with three doors: Find the Mole, Escape Room,
Forensic Lab. It prints a 6-digit PIN, the players' address, a host link
(`/host?k=...`, open it only on the host laptop), and the game seeds.

`live.py` holds the lab state (`LiveState`):
- `issue(employee, fmt)`: registered, recorded copy (txt, docx, pdf, png).
- `analyse(name, data)`: save under a generated name, intake (read-only original,
  working copy, SHA-256, custody entry), then `forensics.examine`. A photo with no
  readable text is read for C7 dots instead (station byte -> pool of copies).
- `make_server(state, host, port, game=..., escape=...)` wires the apps.

Other commands in `cli_live.py`:
- `molehunt examine leak.txt --master m.md --employees r.csv [--html out.html]`
- `molehunt forward --from E007 --to C12 --master M1 -o c12.txt`

Safety: PIN, host key, 2 MB cap, file-type allow-list, no client paths,
synthetic data, no outbound traffic, LAN only.

Worked example: a guest downloads E005's copy, retypes it, uploads it. The lab
page shows LIVE-001, the meter climbing past 2, "attribute E005", the heatmap,
and "partly sanitised" (zero-width and NBSP layers gone, words intact).
