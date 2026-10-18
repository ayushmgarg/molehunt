# Explain: keys

HMAC-SHA256 turns a secret key and a message into a fixed 32-byte digest.
MoleHunt prefixes each message with a version and a named purpose (the domain).
Every field has a two-byte length, so `ab` cannot be confused with `a`, `b`.
Different domains keep codeword bits separate from placement and bias draws.

`lowest_bit` reads the final digest byte's low bit, producing 0 or 1.
`keyed_order` sorts indexes by their keyed digest to make a repeatable permutation.
`load_or_create_key` uses exclusive file creation, so it never overwrites an old key.
The default key is 32 random bytes, created by the operating system RNG.

Worked example: frame domain `doc` and field `a` as
`molehunt:v1 | 00 03 | doc | 00 01 | a`, then calculate HMAC-SHA256.
For any fixed key, the same framed input yields the same digest and bit.
A different domain changes the input even when the employee and slot are unchanged.

This module does not store or transmit keys beyond the caller's chosen file.
