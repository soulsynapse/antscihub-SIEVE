---
title: The product owns the word "tools"
adr: 5
position: "03.01"
status: settled
decided: 2026-08-06
---

"Tools" means pipeline steps and nothing else; repo machinery lives in
`scripts/`, which is not a package and must not become one.

Why: with `src/sieve/tools/` as the product's customization surface, a
machinery folder under the same noun would make one word mean two things in
one tree — every grep and every conversation would pay for it. Decided with
the rename of `tools/doc_index.py` to `scripts/doc_index.py`.
