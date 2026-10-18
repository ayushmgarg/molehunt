# Explain: synthetic roster and background logs

Roster: `synthetic_roster(n, seed)` builds names from invented syllables and
surnames (no real people), plus a department and role. IDs are E001..En.
`data/demo/roster50.csv` is the 50-person roster used by the benchmark (seed 0).

Background logs model ordinary office activity so that a planted event is not
the only row in a file. For each employee and day, events follow a Poisson
process: gaps are exponential with mean `600 / daily_rate` minutes inside the
08:00-18:00 window. Expected events per person per day = `daily_rate`.

Worked example: 12 employees, 5 days, rate 3 gives about 12 x 5 x 3 = 180 rows.
With `random.Random(9)` the same 180-odd rows come out every run, sorted by time.
Device IDs are `WS-<id>` and IPs fall in the private 10.20.x.y range.
