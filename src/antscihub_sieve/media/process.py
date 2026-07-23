from __future__ import annotations

import subprocess


# Prevent FFmpeg and FFprobe from flashing console windows when SIEVE is
# launched through the Windows GUI entry point. The value is zero elsewhere.
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
