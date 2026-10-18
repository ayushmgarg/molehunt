# Explain: live LAN demo

`molehunt live` turns the host laptop into a small web server on the local network.

- `/` (participant): choose an employee, enter the PIN, download a fingerprinted
  copy (issued and recorded like `molehunt issue`). Upload a leak as a file or as
  pasted text.
- Upload handling: save under a generated name, intake it (read-only original,
  working copy, SHA-256, custody entry), then run the same analysis as the CLI.
  A PNG photo is read for C7 dots; the station byte is compared with each
  employee's keyed PDF station byte (HMAC(K, "pdf-dots", id)), giving a pool.
- `/board` (host, projector): newest leak first: hash, slots read, outcome, top
  copy, LR, and the top-5 ranking; it reloads every 3 s. `/board.json` has the
  same data.

Safety: random 6-digit PIN per run, 2 MB limit, file-type allow-list, no client
paths, synthetic data only, no outbound traffic.

Worked example: a participant downloads E005's copy, retypes it (A5), uploads it.
The board shows LIVE-001, 170/265 slots, "attribute: E005", log10 LR about 37.
