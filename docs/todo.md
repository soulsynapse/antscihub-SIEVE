# Todo

List of things that need to get built. Kept deliberately short so the todo doesn't go stale. Max 5 items.

For any given todo, see if the tree already answers how to implement it, and raise if something else should be done before it.

The todo item leaves the file when it is done.

- A keyed collection of series, so a re-key strands nothing: `chain.key`
  changes under a parameter, and nothing holds the series it left behind
- Port pool.py's refcount eviction into `store.Frames`, which still evicts
  on a count budget no consumer is consulted about
- A tool that accepts a field as an input