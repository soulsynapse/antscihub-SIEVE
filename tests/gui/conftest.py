"""GUI test fixtures. Every test in this package needs a Qt runtime."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from sieve.gui.document import ReplicateDocument

# The `gui` marker is declared per module, not here: pytest reads `pytestmark`
# from test modules and classes only, so a conftest-level one is silently inert.


#: Length of the source the `document` fixture binds. Named because the clip
#: tests assert against it: a mark past the end lands here, and an in point on
#: its own runs to here.
SOURCE_FRAMES = 1000


@pytest.fixture
def document(qapp: object) -> Iterator[ReplicateDocument]:
    """A fresh document bound to a 1000x800 source, 1000 frames long."""
    del qapp
    doc = ReplicateDocument()
    doc.bind_source(1000, 800, SOURCE_FRAMES)
    yield doc
    doc.deleteLater()
