# Running the LAN party (Find the Mole, Escape Room, Forensic Lab)

Host = the laptop running MoleHunt (connected to the projector). Players = phones
or laptops on the **same Wi-Fi**. Nothing goes to the internet.

## 1. Start the server (host)

```bash
uv run molehunt init        # once per machine
uv run molehunt live
```

It prints:

```text
PIN for players: 482913
Players open:   http://192.168.1.23:8765/
Host console:   http://127.0.0.1:8765/host?k=Xy...      (this laptop only)
Seeds (for the log): game 123..., escape 456...
```

- Open the **Host console** link in the host's browser. It unlocks the projector
  screens. Never share this link: it is the host's password.
- Tell players the **Players open** address and the **PIN**.
- If phones cannot connect: set the Wi-Fi to **Private** in Windows settings and
  allow Python through the firewall when asked. Use the 192.168.x.x / 10.x.x.x address.
- Options: `--minutes 20` (escape clock), `--port 9000`, `--master <file>`.

## 2. Find the Mole (4-30 players, ~10 min per round)

1. Projector: Host console -> **Find the Mole screen**. Players: open the address ->
   Find the Mole -> nickname + PIN. Each phone shows that player's own copy.
2. Host presses a mode: **One mole**, **Mole forwards to a journalist**, or **Two double agents**.
3. The mole's phone says "You are the mole": pick up to 2 scrub tools, press Leak.
   Everyone else just sees "Lights out".
4. The leak appears on the projector and phones. Players compare it with their own
   copy (the facts differ per copy!), spend 3 forensic tokens, and bet 1-3 chips.
5. Host presses **Run the forensics**. The meter climbs slot by slot, the heatmap
   colours the leak, the family tree shows the path, then the truth and scores.

## 3. Escape Room (teams of 2-4, 30 min)

1. Projector: Host console -> **Escape Room screen**. Teams: Escape Room -> team
   name + PIN. Every team gets its own case.
2. Host presses **Start the clock**.
3. Each lock: read the story, download the files, use the tool on the page, type
   the answer. Hints cost 120 s, wrong answers 30 s. The projector ranks teams live.

## 4. Forensic Lab (free play)

Home -> Forensic Lab: download a copy for an employee, change it any way (edit,
retype, cut, scrub, print and photograph), upload it. The case page shows the
custody hash, the meter, heatmap, canary facts, scrub check, and the tree.
The projector board (`/board`) lists every case as it arrives.

## Troubleshooting

| Problem | Fix |
|---|---|
| "wrong PIN" | the PIN changes every run; read it from the terminal |
| "host only" | open the Host console link on the host laptop first |
| port busy | another `molehunt live` is running; close it or use `--port` |
| photo not read | flat, well lit, whole page; PNG copies from the lab work best |
