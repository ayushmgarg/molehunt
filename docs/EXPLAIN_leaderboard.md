# Explain: graded submissions and leaderboard

`record_graded` stores every submission with its full score breakdown.
- correct and total >= 60 -> case `complete`;
- third wrong submission -> case `closed` with the partial score;
- otherwise the case stays `in_progress`.
When a case completes or closes, the next case unlocks with all tools earned so far.

`leaderboard` sums each player's case scores and counts finished cases, sorted by
points, then finished cases, then player id.

Worked example: p1 submits 55 (correct but below 60, stays open) then 92 ->
complete, 92 points. p2 is wrong three times -> closed with 12. Ranking: p1, p2.
