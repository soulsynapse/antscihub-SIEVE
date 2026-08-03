"""The store: every value ever computed, addressed by recipe hash.

Content-addressed, never invalidated -- a param change names a new hash
that isn't in the store yet. Old entries age out under a size budget
(ARCHITECTURE.md "The store"; DESIGN-SESSION.md Exchange 5, "Delete
invalidation rather than owning it"). The hash definition's home --
here, the executor, or beside the kernel as its own interpreter -- is
genuinely open and comes due with this module's first real code.
"""

from sieve.debt import Owed

raise Owed(
    "20260802T023507Z: content-addressed store: recipe-hash addressing over the logical graph,"
    " size-budget aging, no invalidation; ARCHITECTURE.md 'The store',"
    " DESIGN-SESSION.md Exchange 5"
)
