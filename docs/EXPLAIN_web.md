# Explain: LAN web layer (molehunt/web/)

Stdlib only; no framework, no internet. Files:

- `server.py`: parses a request once (query, form or multipart upload, cookies)
  and asks each app in turn; errors become a themed page with 400/403/404.
  2 MB body cap. On Windows `allow_reuse_address` is off so two servers cannot
  silently share one port.
- `hub.py`: home `/` (three doors), host console `/host?k=<key>` (cookie), PIN check.
- `theme.py`: one Halloween stylesheet, inline bats/moon/fog, Lucide icons, fonts
  served from `web/static` (Creepster OFL, Special Elite Apache-2.0). `poll=(url,
  version)` reloads a page when the version text changes (2 s fetch loop).
- `findings.py`: verdict, attribution-o-meter (SVG dial; script steps through the
  evidence curve), heatmap, canary facts, scrub check, family tree, ranking.
- `lab_app.py`: get a copy / leak it / case page / projector board.
- `game_app.py` + `game_pages.py`: Find the Mole routes and screens.
- `escape_app.py`: escape-room routes and screens; tools run outside the room lock.

Identity: players get a random cookie (`mh_game`, `mh_team`); the host gets
`mh_host` equal to the host key printed in the terminal.

Worked example: a phone posts `/game/bet` with suspect=A03, chips=2; the app
records it, bumps `game.version`; the projector's poll sees a new version within
2 s and reloads to show "Bets placed: 3/4".
