# Live demo across two laptops: test steps

Host = laptop running MoleHunt. Guest = second laptop or phone. Same Wi-Fi.

1. Host: `uv run molehunt init` (once), then `uv run molehunt live`.
   It prints a PIN and one "Join" URL per network adapter. Use the one that
   starts like 192.168.x.x or 10.x.x.x on the Wi-Fi adapter.
2. Host: if Windows asks, allow Python on **Private** networks. If the guest
   cannot connect, the network is probably set to Public (Settings > Network >
   Wi-Fi > Private) or the firewall blocked port 8765.
3. Guest: open the Join URL, pick an employee (for example E007), enter the PIN,
   download a copy (txt, docx, pdf or png).
4. Guest: change the copy any way you like (retype bits, delete paragraphs,
   paste into a chat app and back), then upload it or paste it on the same page.
5. Host: open the Board URL on the projector. Within 3 seconds it shows the leak,
   its SHA-256, slots read, the ranking and the finding.
6. Optional print test: download the PDF or PNG, print it, photograph the page
   flat and well lit, and upload the photo (.jpg). The OCR reads the text; if no
   text is readable, the yellow dots are decoded instead.

What to report back: did the guest connect, which formats worked, what the board
said for each leak, and whether the printed-photo upload was read.
