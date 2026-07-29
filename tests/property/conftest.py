







from __future__ import annotations

from hypothesis import HealthCheck, settings

settings.register_profile(
    "property",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("property")
