# Explain: examiner report

`report.py` builds a neutral list of sections; `report_render.py` writes the
same sections to DOCX (python-docx) or PDF (reportlab), so both formats agree.

Section 8 skeleton, in order:
1. Case and scope: case id, examiner, UTC date, question asked.
2. Evidence: file and SHA-256; a table with intake time and custody status.
3. Method: channels used, LR = (1-e)^m e^(n-m) / 0.5^n, tool version, and the
   SHA-256 of `bench/results/runs.csv` as the validation reference.
4. Findings: per-channel observed/total, ranking, and the decision statement
   with its verbal LR phrase.
5. Log fusion and correlation: prior, posterior, applied factors, timeline rows.
6. Limitations: copy vs person, erasure rate = 1 - n/L, alternative hypotheses,
   and the false-accusation rate read from `bench/results/summary.json`.
7. Conclusion in standard wording (attribute / cannot distinguish / none).
8. Appendix: slot matrix (o match, x mismatch, - erasure) and a hex excerpt.

Missing inputs are written as "not recorded" or "unknown", never guessed.

Worked example: 60 of 80 slots observed gives "Erasure rate: 25.0%". With no
benchmark on file the report says "error rate unknown".
