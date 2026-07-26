"""GUI test fixtures. Every test in this package needs a Qt runtime."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from sieve.gui.document import ReplicateDocument

# The `gui` marker is declared per module, not here: pytest reads `pytestmark`
# from test modules and classes only, so a conftest-level one is silently inert.


@pytest.fixture
def document(qapp: object) -> Iterator[ReplicateDocument]:
    """A fresh document bound to a 1000x800 source."""
    del qapp
    doc = ReplicateDocument()
    doc.bind_source(1000, 800)
    yield doc
    doc.deleteLater()
