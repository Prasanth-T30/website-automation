# Mentor signatures

One PNG per mentor, named after their `id` in `app/core/constants.py`
(`MENTORS`) — for example `sahana.png` for the mentor with `id="sahana"`.

Transparent background, and roughly the proportions of `../signature.png`
(315x99). The renderer scales to a fixed width on the certificate's right-hand
rule, so what matters is the aspect ratio, not the pixel size.

A file that is absent is not an error: the mentor's name and "Mentor" still
print, with the rule left unsigned. That is deliberate — a certificate should
never be blocked by a missing image.
