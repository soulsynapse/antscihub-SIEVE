"""Re-exports the package's public interface from ``style.py``, so callers'
``from ...gui.style import apply`` doesn't change regardless of what this
package's internals look like."""

from proto_sieve.src.sieve.gui.style.style import (
    ROLE_BAR,
    apply,
    apply_title_bar,
    bar_height,
    tag,
)

__all__ = ["apply", "apply_title_bar", "tag", "bar_height", "ROLE_BAR"]
