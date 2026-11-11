# Reduced extension utility tests

Six backend successes. Constructed reduced graphs, not full-source workflow certifications. No models or downloads. Full [receipts](utilities.json).

| Capability | Seconds | Contract | Caveat |
|---|---:|---|---|
| desaturate | 0.33 | True | backend capability only |
| gif | 0.65 | True | backend capability only |
| overlay | 0.33 | True | iTools loaded/source identity uncertain |
| previews | 0.66 | True | backend capability only |
| prompt-record | 0.99 | True | iTools loaded/source identity uncertain |
| stitch | 0.34 | True | backend capability only |

The original first-pass validators checked GIF frame count and non-empty preview evidence. A later independent review found those checks too weak: the runner now decodes every GIF frame and requires both preview node outputs. Existing artifacts were separately rechecked; see `utility-revalidation.json`. Further runs refuse source files newer than the server process and unexpected schema providers. No server restart was performed.
