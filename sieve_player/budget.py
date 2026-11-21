"""What each holder of results may take, shared out of the machine's memory read once: where half
of it has room for every ceiling here each limit is its ceiling, and on a smaller machine all shrink
in proportion until together they fit it. `SIEVE_MEMORY_GB` stands for the half, and `SIEVE_MEMO_GB`
and `SIEVE_CACHE_GB` set their own holder's limit over the share. Nothing of the player is imported.
"""
import functools
import os

import psutil

CEILINGS = {"cache": 4 << 30, "memo": 4 << 30, "stack": 512 << 20, "held": 512 << 20, "hold": 64 << 20}
HELD_AT_ONCE = {"cache": 1, "memo": 1, "stack": 4, "held": 1, "hold": 2}   # the worker's four walks; the bare process's memo and cache
SHARE = 0.5
TOTAL_ENV, MEMO_ENV, CACHE_ENV = "SIEVE_MEMORY_GB", "SIEVE_MEMO_GB", "SIEVE_CACHE_GB"
OVERRIDES = {"memo": MEMO_ENV, "cache": CACHE_ENV}


def gb(env, environ):
    """The bytes `environ[env]` names in GB, or None where it is unset, zero or not a number."""
    try:
        return int(float(environ[env]) * 2**30) or None
    except (KeyError, ValueError):
        return None


def limits(ram, environ):
    """Each holder's limit in bytes, by CEILINGS' keys, on a machine of `ram` bytes under the
    variables in `environ`; a limit is of one holder, HELD_AT_ONCE says how many share the total."""
    total = gb(TOTAL_ENV, environ) or ram * SHARE
    scale = min(1.0, total / sum(CEILINGS[k] * HELD_AT_ONCE[k] for k in CEILINGS))
    out = {k: int(v * scale) for k, v in CEILINGS.items()}
    out.update({k: b for k, env in OVERRIDES.items() if (b := gb(env, environ))})
    return out


@functools.cache
def here():
    """limits() for this machine and process environment, read the first time it is asked."""
    return limits(psutil.virtual_memory().total, os.environ)
