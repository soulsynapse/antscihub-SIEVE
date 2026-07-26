"""Hypothesis configuration for the property suite.

Deadlines are off. Every property here exercises a pure function that runs in
microseconds, so a per-example deadline can only ever fire on a scheduling
hiccup — a flaky failure that says nothing about the code. Example count stays
at the default; these shrink fast and the suite is on the fast feedback loop.
"""

from __future__ import annotations

from hypothesis import HealthCheck, settings

settings.register_profile(
    "property",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("property")
