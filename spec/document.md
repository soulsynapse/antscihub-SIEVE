# The document

A SIEVE document is the saved form of a pipeline: which tools, how they are wired, where they sit
on the canvas, what their params are, which node the frame shows, and which video is loaded. The
document is its own module so that the canvas, the runtime, or both can be rewritten and every
saved document still opens. The dependency runs one way: the canvas and the window read and write
documents through this module; this module knows nothing about either.

## Document module

Assumes: nothing.

- [x] A module under `sieve_player` holds the document type and its load and save, and importing it
  imports neither Qt nor the canvas nor the window nor cv2.
  Check: a test in `tests/` imports the module in a subprocess and asserts those names are absent
  from `sys.modules`.
- [x] A document holds nodes, each with an id, a tool name, a params dict, and a position; wires,
  each naming a source node and a destination node and the destination's input; the id of the
  node that carries the display flag, or none; and the video path, or none.
  Check: a test constructs one and reads each back.
- [x] A document saved to a file and loaded again is equal to the one saved, including positions
  and params.
  Check: a test in `tests/`.
- [x] The file is JSON, carries a format version, and is readable by a person: node ids and tool
  names appear as written.
  Check: a test asserts the version key and that `json.load` on the file succeeds.
- [x] Loading a file whose version is newer than the module knows fails with an error that names
  both versions, and loads nothing.
  Check: a test in `tests/`.
- [x] Loading a file whose tool names the registry does not resolve succeeds; the node is kept with
  its name, params and position, and is marked unresolved. Saving it again writes it back unchanged.
  Check: a test loads a document naming a tool that does not exist and round-trips it.
- [x] A key the module does not know, at the top level or on a node, survives load and save.
  Check: a test adds a foreign key and round-trips.
- [x] A document built from a plain list of tools wires each to the nearest earlier tool that
  produces what it expects, the video node first, and lays the nodes out top to bottom. This is
  how `play([gray, threshold])` keeps working.
  Check: a test builds from a list and asserts the wires.
- [x] Validation is a function of the document and the tools' declared types, and of nothing
  else: it reports every wire whose destination does not expect what its source produces, every
  cycle, and every node with an input nothing feeds. It reports; it does not refuse to load.
  Check: a test for each of the three.
- [x] The video path is stored as written. On load, a relative path is resolved against the
  document's own folder; an absolute path is used as is. A path that does not resolve is still
  loaded, and the window reports it as a path that will not open.
  Check: a test saves a document beside a video with a relative path, moves both, and loads.

## Non-goals

- A binary or compressed format. JSON is diffable and readable, and a pipeline is small.
- Embedding the video or the frames. The document names the video; it is not a project archive.
- Migrating older formats on load. There are no older formats yet. When the version changes, the
  migration becomes a deliverable here.
