# Device names are filename-safe by construction, enforced at setup and at export

The device name is carried into the end-of-day export as the Stock sheet
report file's name component (`stocks-<device name>.csv`, see ADR-0003). We
made filename safety a rule on the Device name itself: the register rejects a
name at setup that contains a path separator or traversal, a Windows-illegal
character, a reserved device name (`CON`, `NUL`, `COM1–9`, `LPT1–9`), a control
character, or one long enough to overflow the NTFS 255-character limit (once
the `stocks-`/`.csv` shell is accounted for).

We chose a Windows reject-list over a strict portable allow-list because the
register runs only on Windows laptops (CONTEXT.md: Device) and the reject-list
keeps every legitimate name such as `Till A` or `Till A 2` working. Enforcing
at both seams closes the gap left by names already persisted before the rule
existed: the export guard makes the chosen folder the final authority no matter
how the name got in, so an unsafe name can never escape it.