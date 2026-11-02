# Sources: crops as a varying source under one pipeline

Planned, 2026-11-01, not built. A document holds a list of sources, each a plate reference, a rect, a
scale, a name and an id hashed from those, and the pipeline below the video node is the one thing;
the GUI shows one source at a time, reading the plate and slicing live until the source is
materialized to a crop clip with a sidecar (plate, rect, scale, codec, quality, true row count, key
stamp), after which the video node reads the file. Materializing groups sources by plate and cuts
every rect in one decode pass through the off-GUI compute path, so the fan-out is a loop over rects
inside one function and the walk, memo and series heads never see N of anything; the prefix stays a
record of parameters, not a sub-graph, until a real case needs more, at which point a stamped cache
tool is the design that sits beside this one. Open: the default quality, settled by a finding that
runs one chain over a raw crop and the same crop at two qualities; the shape of a document with no
sources is the plate as one source with the full frame as its rect.
