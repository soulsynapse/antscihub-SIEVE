"""The pipeline file: intent only, never progress (ARCHITECTURE.md).

Format and loader owe Exchange 1's discipline wholesale: per-step
schema_version, an append-only migration registry of pure dict -> dict
functions run before validation, additive-only evolution, unknown-field
preservation on round-trip, and the fixture corpus of one checked-in
file per historical version (DESIGN-SESSION.md, Exchange 1).
"""

from sieve.debt import Owed

raise Owed(
    "20260802T023506Z: pipeline file format and loader: intent-only DAG of steps, per-step"
    " schema_version, migration registry, unknown-field preservation;"
    " ARCHITECTURE.md 'The pipeline', DESIGN-SESSION.md Exchange 1"
)
