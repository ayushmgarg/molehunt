# Explain: codes

Single-leaker mode derives bit `i` as the low bit of
`HMAC(K, frame("cw", employee_id, i))`. Key framing is implemented in `keys.py`.
This makes codewords deterministic for a key while separating employee identities.

Hamming distance counts positions where two codewords differ.
The minimum pairwise distance summarizes the closest pair in a roster.
It is descriptive; random HMAC codewords do not guarantee a target distance.

Worked result: for IDs `E001`–`E050`, length 256, and test key `bytes(range(32))`,
the minimum pairwise Hamming distance is 102.
Changing the key changes the codewords and this measured distance.
