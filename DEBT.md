# DEBT — present, correct debt (hand-authored)

Type-1 debt: real gaps that exist right now. A placeholder in the tree is
one category of this type, tracked automatically in DEBT-AUTO.txt; entries
here are the gaps no marker can carry. Nothing goes here that is not
presently owed.

- **Adapter naming asymmetry** (tests/conftest.py, since 2026-08-01): a
  statically invisible Owed raised at import time of a test_*.py file fails
  the suite as a plain collection error with the Owed traceback, without the
  explicit "a marker the enumerator cannot see" naming that call-phase
  nonmembers get. Loud and red, but not named per the plan's letter.
