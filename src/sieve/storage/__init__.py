"""What SIEVE writes at rest, and nothing about what it means.

The layer contract puts `storage/` beside `decode/`: below the pipeline, above
core. A module here knows a file format and an array; it never knows a cache
key, a replicate, or a project. That split is what keeps `crop_writer.py`
testable without a document and keeps identity derivation in one place
(`pipeline/materialize.py` decides what a file *is*; this package only puts
bytes in it).
"""
