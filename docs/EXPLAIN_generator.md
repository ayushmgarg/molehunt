# Explain: case generator

Input: case YAML + player seed. Effective seed = seed + case offset; it drives one
`random.Random` and the case key SHA-256("MoleHunt case seed v1", case id, seed).
Output: `public/` (evidence, roster, issuance registry, logs) and
`private/ground_truth.json` (owner, slots, planted events, evidence SHA-256).
Only authored slots are used (front matter stripped): players read slots without K.

Per case (builders in `case_evidence.py`):
1. Invisible Ink: C1 mark after every slot word, one CMS decoy U+200D off-slot.
2. Canary Trap: reporter rewrites slot words (erasures) so leaker and a twin tie
   on the first 20 readable slots, then A5 retype removes C1/C2.
3. Yellow Dots: aligned `scan.png`, yellow-dot `photo.png` rotated 2-4 degrees
   with noise and JPEG, print jobs, badge log; truth pool = all who printed there.
4. Revision Trail: rsid fingerprint; author cleared, lastModifiedBy and Template
   point at decoys; public rsid and template registries.
5. Half a Page: ~35% of lines kept, where leaker and twin agree; A5 + A4; twin on
   leave (leave calendar), leaker has an after-hours download.
6. Two Moles: Tardos code on a 155-slot master, majority merge, 2% bit noise.
7. Borrowed Copy: owner on leave; login 02:13 / download 02:14 from a VPN IP that
   DHCP maps to the actor's workstation; actor badged in at 01:50.

Worked example: seed 7 for Case 1 gives the same leak bytes and truth every run.
