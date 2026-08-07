window.GRAPH_DATA = {
 "meta": {
  "root": "sieve",
  "bands": [
   [
    "sieve.gui",
    "sieve.cli"
   ],
   [
    "sieve.bench"
   ],
   [
    "sieve.pipeline",
    "sieve.workers"
   ],
   [
    "sieve.filters"
   ],
   [
    "sieve.decode",
    "sieve.storage",
    "sieve.backend",
    "sieve.detect"
   ],
   [
    "sieve.mutual"
   ],
   [
    "sieve.core"
   ]
  ],
  "moduleCount": 124,
  "ghostCount": 18,
  "edgeCount": 435
 },
 "modules": {
  "sieve.__init__": {
   "package": "sieve",
   "layerPackage": null,
   "band": null,
   "loc": 7,
   "isInit": true,
   "ghost": false,
   "doc": "The runtime-importable version string: what the CLI `--version` flag and the",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.backend.__init__": {
   "package": "sieve.backend",
   "layerPackage": "sieve.backend",
   "band": 4,
   "loc": 8,
   "isInit": true,
   "ghost": false,
   "doc": "Device policy and backend identity. Holds no filter's implementation.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.backend.dispatch": {
   "package": "sieve.backend",
   "layerPackage": "sieve.backend",
   "band": 4,
   "loc": 579,
   "isInit": false,
   "ghost": false,
   "doc": "Which kernel runs: a shelf keyed by `(filter_id, version, backend)`.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "enum",
    "importlib",
    "typing"
   ],
   "symbols": [
    {
     "name": "Backend",
     "kind": "class",
     "line": 45,
     "loc": 8,
     "doc": "A device family a kernel can be written against."
    },
    {
     "name": "Kernel",
     "kind": "class",
     "line": 73,
     "loc": 12,
     "doc": "One frame in, one frame out, on one backend."
    },
    {
     "name": "MergingKernel",
     "kind": "class",
     "line": 87,
     "loc": 24,
     "doc": "One frame per input port in, one frame out, on one backend."
    },
    {
     "name": "WindowedKernel",
     "kind": "class",
     "line": 113,
     "loc": 14,
     "doc": "A consecutive input span in, one frame-shaped output, on one backend."
    },
    {
     "name": "StatefulKernel",
     "kind": "class",
     "line": 129,
     "loc": 17,
     "doc": "The same shape, plus somewhere to keep what the last frame taught it."
    },
    {
     "name": "unrunnable_reason",
     "kind": "function",
     "line": 148,
     "loc": 73,
     "doc": "Why no protocol above can call `spec`, or `None` if one can."
    },
    {
     "name": "DuplicateKernelError",
     "kind": "class",
     "line": 223,
     "loc": 2,
     "doc": "Two kernels claim the same filter, version, and backend."
    },
    {
     "name": "NoKernelError",
     "kind": "class",
     "line": 227,
     "loc": 2,
     "doc": "No registered kernel for this filter can run on this machine."
    },
    {
     "name": "KernelBinding",
     "kind": "class",
     "line": 232,
     "loc": 37,
     "doc": "The kernel `select` chose, which backend it came from, and how to start it."
    },
    {
     "name": "runtime_available",
     "kind": "function",
     "line": 271,
     "loc": 13,
     "doc": "Whether this machine could execute a kernel for `backend` at all."
    },
    {
     "name": "KernelRegistry",
     "kind": "class",
     "line": 286,
     "loc": 100,
     "doc": "Lookup from a spec and a backend to the callable that implements it."
    },
    {
     "name": "kernel",
     "kind": "function",
     "line": 392,
     "loc": 47,
     "doc": "Decorate a function as `params_model`'s kernel on `backend`."
    },
    {
     "name": "merging_kernel",
     "kind": "function",
     "line": 441,
     "loc": 42,
     "doc": "Decorate a mapping-taking function as `params_model`'s kernel on `backend`."
    },
    {
     "name": "windowed_kernel",
     "kind": "function",
     "line": 485,
     "loc": 39,
     "doc": "Decorate a span-taking function as `params_model`'s kernel on `backend`."
    },
    {
     "name": "stateful_kernel",
     "kind": "function",
     "line": 526,
     "loc": 53,
     "doc": "Decorate a three-argument function as `params_model`'s kernel on `backend`."
    }
   ],
   "calls": [
    [
     "KernelBinding",
     "Backend"
    ],
    [
     "KernelBinding",
     "Kernel"
    ],
    [
     "KernelBinding",
     "MergingKernel"
    ],
    [
     "KernelBinding",
     "StatefulKernel"
    ],
    [
     "KernelBinding",
     "WindowedKernel"
    ],
    [
     "runtime_available",
     "Backend"
    ],
    [
     "KernelRegistry",
     "Backend"
    ],
    [
     "KernelRegistry",
     "DuplicateKernelError"
    ],
    [
     "KernelRegistry",
     "Kernel"
    ],
    [
     "KernelRegistry",
     "KernelBinding"
    ],
    [
     "KernelRegistry",
     "MergingKernel"
    ],
    [
     "KernelRegistry",
     "NoKernelError"
    ],
    [
     "KernelRegistry",
     "StatefulKernel"
    ],
    [
     "KernelRegistry",
     "WindowedKernel"
    ],
    [
     "KernelRegistry",
     "runtime_available"
    ],
    [
     "kernel",
     "Backend"
    ],
    [
     "kernel",
     "Kernel"
    ],
    [
     "kernel",
     "KernelRegistry"
    ],
    [
     "merging_kernel",
     "Backend"
    ],
    [
     "merging_kernel",
     "KernelRegistry"
    ],
    [
     "merging_kernel",
     "MergingKernel"
    ],
    [
     "windowed_kernel",
     "Backend"
    ],
    [
     "windowed_kernel",
     "KernelRegistry"
    ],
    [
     "windowed_kernel",
     "WindowedKernel"
    ],
    [
     "stateful_kernel",
     "Backend"
    ],
    [
     "stateful_kernel",
     "KernelRegistry"
    ],
    [
     "stateful_kernel",
     "StatefulKernel"
    ]
   ],
   "uses": [
    [
     "Kernel",
     "sieve.core.types",
     "Frame"
    ],
    [
     "MergingKernel",
     "sieve.core.types",
     "Frame"
    ],
    [
     "WindowedKernel",
     "sieve.core.types",
     "Frame"
    ],
    [
     "WindowedKernel",
     "sieve.core.types",
     "FrameSpan"
    ],
    [
     "StatefulKernel",
     "sieve.core.types",
     "Frame"
    ],
    [
     "unrunnable_reason",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "unrunnable_reason",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "unrunnable_reason",
     "sieve.core.filter_base",
     "StreamKind"
    ],
    [
     "KernelRegistry",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "kernel",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "merging_kernel",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "windowed_kernel",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "stateful_kernel",
     "sieve.core.filter_base",
     "Mode"
    ]
   ]
  },
  "sieve.backend.identity": {
   "package": "sieve.backend",
   "layerPackage": "sieve.backend",
   "band": 4,
   "loc": 51,
   "isInit": false,
   "ghost": false,
   "doc": "Backend identity string for cache keys, mirroring `decode/identity.py`.",
   "annotation": "",
   "external": [
    "functools",
    "importlib",
    "numpy"
   ],
   "symbols": [
    {
     "name": "backend_identity",
     "kind": "function",
     "line": 33,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "_cupy_version",
     "kind": "function",
     "line": 39,
     "loc": 12,
     "doc": ""
    }
   ],
   "calls": [
    [
     "backend_identity",
     "_cupy_version"
    ]
   ],
   "uses": [
    [
     "backend_identity",
     "sieve.backend.dispatch",
     "Backend"
    ]
   ]
  },
  "sieve.bench.__init__": {
   "package": "sieve.bench",
   "layerPackage": "sieve.bench",
   "band": 1,
   "loc": 10,
   "isInit": true,
   "ghost": false,
   "doc": "Observation: latency budgets and metric collection.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.bench.budgets": {
   "package": "sieve.bench",
   "layerPackage": "sieve.bench",
   "band": 1,
   "loc": 310,
   "isInit": false,
   "ghost": false,
   "doc": "The latency budget table. Source of truth in code for both speed regimes.",
   "annotation": "",
   "external": [
    "dataclasses",
    "enum"
   ],
   "symbols": [
    {
     "name": "Regime",
     "kind": "class",
     "line": 36,
     "loc": 5,
     "doc": "The two speed regimes. Improving one at the cost of the other is a defect."
    },
    {
     "name": "Budget",
     "kind": "class",
     "line": 44,
     "loc": 11,
     "doc": "One latency ceiling."
    },
    {
     "name": "BudgetMissError",
     "kind": "class",
     "line": 57,
     "loc": 2,
     "doc": "Raised when a measured interval exceeds its budget."
    },
    {
     "name": "_table",
     "kind": "function",
     "line": 61,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "Debt",
     "kind": "class",
     "line": 254,
     "loc": 12,
     "doc": "A budget miss that is declared, scheduled for repayment, and tolerated"
    },
    {
     "name": "check",
     "kind": "function",
     "line": 287,
     "loc": 23,
     "doc": "Assert a measured interval is within its budget."
    }
   ],
   "calls": [
    [
     "Budget",
     "Regime"
    ],
    [
     "_table",
     "Budget"
    ],
    [
     "check",
     "BudgetMissError"
    ],
    [
     "check",
     "Debt"
    ]
   ],
   "uses": []
  },
  "sieve.bench.metrics": {
   "package": "sieve.bench",
   "layerPackage": "sieve.bench",
   "band": 1,
   "loc": 280,
   "isInit": false,
   "ghost": false,
   "doc": "The metric collection bus: where a timed interval goes and who hears it.",
   "annotation": "",
   "external": [
    "collections",
    "contextlib",
    "dataclasses",
    "statistics",
    "threading",
    "time"
   ],
   "symbols": [
    {
     "name": "Sample",
     "kind": "class",
     "line": 68,
     "loc": 32,
     "doc": "One measured interval, already judged against its budget."
    },
    {
     "name": "MetricBus",
     "kind": "class",
     "line": 102,
     "loc": 92,
     "doc": "Publishers on one side, subscribers on the other, nothing in between."
    },
    {
     "name": "Recorder",
     "kind": "class",
     "line": 196,
     "loc": 77,
     "doc": "A subscriber that keeps what it hears, grouped by key."
    }
   ],
   "calls": [
    [
     "MetricBus",
     "Sample"
    ],
    [
     "Recorder",
     "Sample"
    ]
   ],
   "uses": [
    [
     "Sample",
     "sieve.bench.budgets",
     "Budget"
    ],
    [
     "MetricBus",
     "sieve.bench.budgets",
     "BUDGETS"
    ]
   ]
  },
  "sieve.bench.retention_trace": {
   "package": "sieve.bench",
   "layerPackage": "sieve.bench",
   "band": 1,
   "loc": 422,
   "isInit": false,
   "ghost": false,
   "doc": "What the viewport asked for, what it got, and what the render kept.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "json",
    "os",
    "pathlib",
    "threading",
    "typing"
   ],
   "symbols": [
    {
     "name": "AccessEvent",
     "kind": "class",
     "line": 89,
     "loc": 15,
     "doc": "One thing that happened to the retention store, in session order."
    },
    {
     "name": "TraceRecorder",
     "kind": "class",
     "line": 106,
     "loc": 59,
     "doc": "Appends events to a JSON Lines file, or does nothing."
    },
    {
     "name": "recorder_from_env",
     "kind": "function",
     "line": 167,
     "loc": 5,
     "doc": "A recorder writing to `TRACE_ENV_VAR`'s path, or a disabled one."
    },
    {
     "name": "load_trace",
     "kind": "function",
     "line": 181,
     "loc": 17,
     "doc": "Read a trace file back. A truncated final line is dropped, not raised."
    },
    {
     "name": "RetentionSim",
     "kind": "class",
     "line": 203,
     "loc": 23,
     "doc": "A retention policy under simulation: what it keeps and what it drops."
    },
    {
     "name": "RingSim",
     "kind": "class",
     "line": 228,
     "loc": 29,
     "doc": "Plain ring: the oldest frame produced is the first dropped."
    },
    {
     "name": "LruSim",
     "kind": "class",
     "line": 259,
     "loc": 24,
     "doc": "What the ring is today: least *recently used*, reads counting as use."
    },
    {
     "name": "PlayheadDistanceSim",
     "kind": "class",
     "line": 285,
     "loc": 45,
     "doc": "The proposal: drop the retained frame farthest from the playhead."
    },
    {
     "name": "ReplayScore",
     "kind": "class",
     "line": 340,
     "loc": 19,
     "doc": "How one policy would have served one recorded session."
    },
    {
     "name": "replayable",
     "kind": "function",
     "line": 361,
     "loc": 8,
     "doc": "The events a replay acts on: every put, and every get the ring saw."
    },
    {
     "name": "replay",
     "kind": "function",
     "line": 371,
     "loc": 40,
     "doc": "Score `policy` against a recorded session."
    },
    {
     "name": "compare",
     "kind": "function",
     "line": 413,
     "loc": 9,
     "doc": "Every candidate policy scored against one trace at one capacity."
    }
   ],
   "calls": [
    [
     "TraceRecorder",
     "AccessEvent"
    ],
    [
     "recorder_from_env",
     "TraceRecorder"
    ],
    [
     "load_trace",
     "AccessEvent"
    ],
    [
     "replayable",
     "AccessEvent"
    ],
    [
     "replay",
     "AccessEvent"
    ],
    [
     "replay",
     "ReplayScore"
    ],
    [
     "replay",
     "RetentionSim"
    ],
    [
     "replay",
     "replayable"
    ],
    [
     "compare",
     "AccessEvent"
    ],
    [
     "compare",
     "ReplayScore"
    ],
    [
     "compare",
     "replay"
    ]
   ],
   "uses": [
    [
     "replay",
     "sieve.core.request_intent",
     "RequestKind"
    ]
   ]
  },
  "sieve.bench.sweep": {
   "package": "sieve.bench",
   "layerPackage": "sieve.bench",
   "band": 1,
   "loc": 228,
   "isInit": false,
   "ghost": false,
   "doc": "Sweep a cost over core sets and worker counts, so a constant can be judged.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "psutil",
    "statistics"
   ],
   "symbols": [
    {
     "name": "AffinityUnavailableError",
     "kind": "class",
     "line": 38,
     "loc": 7,
     "doc": "Pinning was asked for and the platform refused."
    },
    {
     "name": "CoreSet",
     "kind": "class",
     "line": 48,
     "loc": 9,
     "doc": "CPUs a cell is pinned to, and what to call them in a report."
    },
    {
     "name": "Cell",
     "kind": "class",
     "line": 60,
     "loc": 5,
     "doc": "One point in the design: a core set and a worker count."
    },
    {
     "name": "Reading",
     "kind": "class",
     "line": 68,
     "loc": 21,
     "doc": "Every sample taken at one cell, in the order they were taken."
    },
    {
     "name": "class_core_sets",
     "kind": "function",
     "line": 91,
     "loc": 19,
     "doc": "One core set per performance class, plus the unpinned whole allocation."
    },
    {
     "name": "sized_core_sets",
     "kind": "function",
     "line": 112,
     "loc": 12,
     "doc": "`source` truncated to each size, for the core-count axis."
    },
    {
     "name": "design",
     "kind": "function",
     "line": 126,
     "loc": 14,
     "doc": "The full factorial, skipping cells that ask for more workers than cores."
    },
    {
     "name": "sweep",
     "kind": "function",
     "line": 142,
     "loc": 50,
     "doc": "Measure `objective` at every cell, `repeats` times, interleaved."
    },
    {
     "name": "_pin",
     "kind": "function",
     "line": 194,
     "loc": 14,
     "doc": "Restrict `process` to the cell's cores, or refuse."
    },
    {
     "name": "curvature",
     "kind": "function",
     "line": 210,
     "loc": 18,
     "doc": "Spread of the best reading across worker counts, per core set."
    }
   ],
   "calls": [
    [
     "Cell",
     "CoreSet"
    ],
    [
     "Reading",
     "Cell"
    ],
    [
     "class_core_sets",
     "CoreSet"
    ],
    [
     "sized_core_sets",
     "CoreSet"
    ],
    [
     "design",
     "Cell"
    ],
    [
     "design",
     "CoreSet"
    ],
    [
     "sweep",
     "AffinityUnavailableError"
    ],
    [
     "sweep",
     "Cell"
    ],
    [
     "sweep",
     "Reading"
    ],
    [
     "sweep",
     "_pin"
    ],
    [
     "_pin",
     "AffinityUnavailableError"
    ],
    [
     "_pin",
     "Cell"
    ],
    [
     "curvature",
     "Reading"
    ]
   ],
   "uses": [
    [
     "class_core_sets",
     "sieve.mutual.machine",
     "cpu_classes"
    ]
   ]
  },
  "sieve.cli.__init__": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 24,
   "isInit": true,
   "ghost": false,
   "doc": "The terminal front end: the run path that has no toolkit to hide behind.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.cli.app": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 94,
   "isInit": false,
   "ghost": false,
   "doc": "The `sieve` command: argument parsing and nothing else.",
   "annotation": "",
   "external": [
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "_print_version",
     "kind": "function",
     "line": 69,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "root_options",
     "kind": "function",
     "line": 76,
     "loc": 9,
     "doc": ""
    },
    {
     "name": "main",
     "kind": "function",
     "line": 87,
     "loc": 3,
     "doc": ""
    }
   ],
   "calls": [
    [
     "root_options",
     "_print_version"
    ]
   ],
   "uses": [
    [
     "_print_version",
     "sieve.__init__",
     "__version__"
    ],
    [
     "main",
     "sieve.decode.quiet",
     "silence_raw_format_warning"
    ]
   ]
  },
  "sieve.cli.common": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 188,
   "isInit": false,
   "ghost": false,
   "doc": "The four things every command that opens a project has to do the same way.",
   "annotation": "",
   "external": [
    "pathlib",
    "pydantic",
    "typer"
   ],
   "symbols": [
    {
     "name": "frame_source",
     "kind": "function",
     "line": 55,
     "loc": 28,
     "doc": "The reader a span is decoded through, however many threads it gets."
    },
    {
     "name": "lower_source_contract",
     "kind": "function",
     "line": 85,
     "loc": 26,
     "doc": "Move a safe root crop/area-scale prefix into FFmpeg, or decline."
    },
    {
     "name": "refuse",
     "kind": "function",
     "line": 113,
     "loc": 10,
     "doc": "Print `message` to stderr and hand back the exception to raise."
    },
    {
     "name": "load_project",
     "kind": "function",
     "line": 125,
     "loc": 14,
     "doc": "Parse the project at `path`, or refuse with pydantic's own message."
    },
    {
     "name": "parse_span",
     "kind": "function",
     "line": 141,
     "loc": 20,
     "doc": "`START:END` as a half-open range."
    },
    {
     "name": "span_for",
     "kind": "function",
     "line": 163,
     "loc": 25,
     "doc": "Which frames to work over: the flag, else the project's clip, else the video."
    }
   ],
   "calls": [
    [
     "load_project",
     "refuse"
    ],
    [
     "parse_span",
     "refuse"
    ],
    [
     "span_for",
     "parse_span"
    ],
    [
     "span_for",
     "refuse"
    ]
   ],
   "uses": [
    [
     "frame_source",
     "sieve.decode.ffmpeg",
     "FfmpegLoweredFrameSource"
    ],
    [
     "frame_source",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "frame_source",
     "sieve.decode.prefetch",
     "PrefetchFrameSource"
    ],
    [
     "frame_source",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "lower_source_contract",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "lower_source_contract",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "lower_source_contract",
     "sieve.decode.ffmpeg",
     "ffmpeg_decoder_identity"
    ],
    [
     "lower_source_contract",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "lower_source_contract",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "lower_source_contract",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "lower_source_contract",
     "sieve.pipeline.lowering",
     "lower_resolved_source"
    ],
    [
     "lower_source_contract",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ],
    [
     "load_project",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "parse_span",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "span_for",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "span_for",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "span_for",
     "sieve.decode.reader",
     "VideoReader"
    ]
   ]
  },
  "sieve.cli.detect_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 409,
   "isInit": false,
   "ghost": false,
   "doc": "`sieve detect` \u2014 run a project's graph and print the intervals it claims.",
   "annotation": "",
   "external": [
    "fractions",
    "numpy",
    "pathlib",
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "detect_project",
     "kind": "function",
     "line": 73,
     "loc": 114,
     "doc": "Detect events in a project's replicates and print the intervals."
    },
    {
     "name": "_series_node",
     "kind": "function",
     "line": 189,
     "loc": 69,
     "doc": "The node whose per-frame output is the detector's series, and what it emits."
    },
    {
     "name": "_collect",
     "kind": "function",
     "line": 260,
     "loc": 29,
     "doc": "Run the plan and stack `node_id`'s output into `(T, B)` columns."
    },
    {
     "name": "_label",
     "kind": "function",
     "line": 291,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "_detect_one",
     "kind": "function",
     "line": 295,
     "loc": 19,
     "doc": "The derivation, or `None` for a project that never tuned one."
    },
    {
     "name": "_refuse_detector_without_source_rate",
     "kind": "function",
     "line": 316,
     "loc": 7,
     "doc": "Stop before detector params turn missing source metadata into a param error."
    },
    {
     "name": "_export",
     "kind": "function",
     "line": 325,
     "loc": 22,
     "doc": "Write the tables and say what was written, naming the file left absent."
    },
    {
     "name": "_report",
     "kind": "function",
     "line": 349,
     "loc": 45,
     "doc": "One replicate's intervals, in absolute frames and in seconds."
    },
    {
     "name": "_refuse_unknown",
     "kind": "function",
     "line": 396,
     "loc": 13,
     "doc": "Refuse a `--replicate` naming nothing, *after* the ones that exist ran."
    }
   ],
   "calls": [
    [
     "detect_project",
     "_collect"
    ],
    [
     "detect_project",
     "_detect_one"
    ],
    [
     "detect_project",
     "_export"
    ],
    [
     "detect_project",
     "_label"
    ],
    [
     "detect_project",
     "_refuse_detector_without_source_rate"
    ],
    [
     "detect_project",
     "_refuse_unknown"
    ],
    [
     "detect_project",
     "_report"
    ],
    [
     "detect_project",
     "_series_node"
    ]
   ],
   "uses": [
    [
     "detect_project",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "detect_project",
     "sieve.cli.common",
     "WORKERS_OPTION"
    ],
    [
     "detect_project",
     "sieve.cli.common",
     "frame_source"
    ],
    [
     "detect_project",
     "sieve.cli.common",
     "load_project"
    ],
    [
     "detect_project",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "detect_project",
     "sieve.cli.common",
     "span_for"
    ],
    [
     "detect_project",
     "sieve.core.pipeline_model",
     "resolved_detector"
    ],
    [
     "detect_project",
     "sieve.detect.tables",
     "DetectionExport"
    ],
    [
     "detect_project",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "detect_project",
     "sieve.pipeline.cache",
     "MemoryFrameStore"
    ],
    [
     "detect_project",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "detect_project",
     "sieve.pipeline.dag",
     "GraphError"
    ],
    [
     "detect_project",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "detect_project",
     "sieve.pipeline.resolve_source",
     "resolve"
    ],
    [
     "detect_project",
     "sieve.pipeline.source_home",
     "SourceHome"
    ],
    [
     "_series_node",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_series_node",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "_series_node",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "_series_node",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_collect",
     "sieve.backend.dispatch",
     "NoKernelError"
    ],
    [
     "_collect",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_collect",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "_collect",
     "sieve.pipeline.cache",
     "MemoryFrameStore"
    ],
    [
     "_collect",
     "sieve.pipeline.executor",
     "FrameSource"
    ],
    [
     "_collect",
     "sieve.pipeline.executor",
     "UnrunnableNodeError"
    ],
    [
     "_collect",
     "sieve.pipeline.executor",
     "execute"
    ],
    [
     "_collect",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_label",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_detect_one",
     "sieve.core.ops.wavelet",
     "ALL_CORES"
    ],
    [
     "_detect_one",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "_detect_one",
     "sieve.core.pipeline_model",
     "resolved_detector"
    ],
    [
     "_detect_one",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_detect_one",
     "sieve.filters.detect",
     "DetectParams"
    ],
    [
     "_detect_one",
     "sieve.filters.detect",
     "DetectorUpdate"
    ],
    [
     "_detect_one",
     "sieve.filters.detect",
     "detect"
    ],
    [
     "_refuse_detector_without_source_rate",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_export",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_export",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "_export",
     "sieve.detect.tables",
     "DetectionExport"
    ],
    [
     "_export",
     "sieve.detect.tables",
     "TableVerificationError"
    ],
    [
     "_export",
     "sieve.detect.tables",
     "write_tables"
    ],
    [
     "_report",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "_report",
     "sieve.filters.detect",
     "DetectorUpdate"
    ],
    [
     "_refuse_unknown",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_refuse_unknown",
     "sieve.core.pipeline_model",
     "Project"
    ]
   ]
  },
  "sieve.cli.inspect_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 231,
   "isInit": false,
   "ghost": false,
   "doc": "`sieve inspect` \u2014 what filters this build has, and what one of them declares.",
   "annotation": "",
   "external": [
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "inspect_filters",
     "kind": "function",
     "line": 37,
     "loc": 29,
     "doc": "List the installed filters, or describe one of them."
    },
    {
     "name": "_resolve",
     "kind": "function",
     "line": 68,
     "loc": 22,
     "doc": "The spec named, newest version when unqualified."
    },
    {
     "name": "_list",
     "kind": "function",
     "line": 92,
     "loc": 17,
     "doc": "One line per registered `(id, version)`, id and version column-aligned."
    },
    {
     "name": "_warmup_note",
     "kind": "function",
     "line": 111,
     "loc": 11,
     "doc": "Say when the number above is a bound rather than what a run pays."
    },
    {
     "name": "_settling_epsilon",
     "kind": "function",
     "line": 124,
     "loc": 3,
     "doc": "Render the epsilon field without making absence look numeric."
    },
    {
     "name": "_describe",
     "kind": "function",
     "line": 129,
     "loc": 33,
     "doc": "Everything `spec` declares, as text."
    },
    {
     "name": "_parameters",
     "kind": "function",
     "line": 183,
     "loc": 31,
     "doc": "One line per field of the params model, primaries marked with `*`."
    },
    {
     "name": "_guidance",
     "kind": "function",
     "line": 216,
     "loc": 15,
     "doc": "The colocated markdown, or a line saying where it would be."
    }
   ],
   "calls": [
    [
     "inspect_filters",
     "_describe"
    ],
    [
     "inspect_filters",
     "_list"
    ],
    [
     "inspect_filters",
     "_resolve"
    ],
    [
     "_describe",
     "_guidance"
    ],
    [
     "_describe",
     "_parameters"
    ],
    [
     "_describe",
     "_settling_epsilon"
    ],
    [
     "_describe",
     "_warmup_note"
    ]
   ],
   "uses": [
    [
     "inspect_filters",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "_resolve",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_resolve",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "_resolve",
     "sieve.core.filter_registry",
     "UnknownFilterError"
    ],
    [
     "_list",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_warmup_note",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_warmup_note",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "_settling_epsilon",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_describe",
     "sieve.backend.dispatch",
     "KERNELS"
    ],
    [
     "_describe",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_describe",
     "sieve.pipeline.cache_key",
     "is_cacheable"
    ],
    [
     "_parameters",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_guidance",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_guidance",
     "sieve.filters.__init__",
     "guidance_path"
    ]
   ]
  },
  "sieve.cli.materialize_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 113,
   "isInit": false,
   "ghost": false,
   "doc": "`sieve materialize` \u2014 cut one replicate's crop to a file and record it.",
   "annotation": "",
   "external": [
    "pathlib",
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "materialize_replicate",
     "kind": "function",
     "line": 46,
     "loc": 49,
     "doc": ""
    },
    {
     "name": "_target",
     "kind": "function",
     "line": 97,
     "loc": 16,
     "doc": ""
    }
   ],
   "calls": [
    [
     "materialize_replicate",
     "_target"
    ]
   ],
   "uses": [
    [
     "materialize_replicate",
     "sieve.cli.common",
     "load_project"
    ],
    [
     "materialize_replicate",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "materialize_replicate",
     "sieve.cli.common",
     "span_for"
    ],
    [
     "materialize_replicate",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "materialize_replicate",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "materialize_replicate",
     "sieve.pipeline.dag",
     "graph_needs_chroma"
    ],
    [
     "materialize_replicate",
     "sieve.pipeline.materialize",
     "CropVerificationError"
    ],
    [
     "materialize_replicate",
     "sieve.pipeline.materialize",
     "MaterializeCancelledError"
    ],
    [
     "materialize_replicate",
     "sieve.pipeline.materialize",
     "materialize_crop"
    ],
    [
     "materialize_replicate",
     "sieve.storage.crop_writer",
     "CropWriteError"
    ],
    [
     "_target",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_target",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_target",
     "sieve.core.replicates",
     "Replicate"
    ]
   ]
  },
  "sieve.cli.preview_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 402,
   "isInit": false,
   "ghost": false,
   "doc": "`sieve preview` \u2014 the tuning loop's inner step, with the timings printed.",
   "annotation": "",
   "external": [
    "collections",
    "json",
    "pathlib",
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "preview_project",
     "kind": "function",
     "line": 67,
     "loc": 142,
     "doc": "Render a project's representative clip and report what it cost."
    },
    {
     "name": "_render",
     "kind": "function",
     "line": 211,
     "loc": 13,
     "doc": "One render, with every deliberate refusal turned into an exit."
    },
    {
     "name": "_target",
     "kind": "function",
     "line": 226,
     "loc": 16,
     "doc": "The arena to preview: the named one, else the first, else the baseline."
    },
    {
     "name": "_parse_edits",
     "kind": "function",
     "line": 244,
     "loc": 27,
     "doc": "`NODE:PARAM=VALUE` triples, with the node checked and the value JSON."
    },
    {
     "name": "_apply",
     "kind": "function",
     "line": 273,
     "loc": 30,
     "doc": "The project with every edit applied to the arena being previewed."
    },
    {
     "name": "_header",
     "kind": "function",
     "line": 305,
     "loc": 29,
     "doc": "One line naming what is being previewed, before anything is rendered."
    },
    {
     "name": "_describe",
     "kind": "function",
     "line": 336,
     "loc": 21,
     "doc": "One render's line: what it covered, what it cost, and what it reused."
    },
    {
     "name": "_timings",
     "kind": "function",
     "line": 359,
     "loc": 22,
     "doc": "One budget's line: the median against the ceiling, and the worst sample."
    },
    {
     "name": "_sequence",
     "kind": "function",
     "line": 388,
     "loc": 14,
     "doc": "The samples in arrival order, while there are few enough to read."
    }
   ],
   "calls": [
    [
     "preview_project",
     "_apply"
    ],
    [
     "preview_project",
     "_describe"
    ],
    [
     "preview_project",
     "_header"
    ],
    [
     "preview_project",
     "_parse_edits"
    ],
    [
     "preview_project",
     "_render"
    ],
    [
     "preview_project",
     "_target"
    ],
    [
     "preview_project",
     "_timings"
    ],
    [
     "_timings",
     "_sequence"
    ]
   ],
   "uses": [
    [
     "preview_project",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "preview_project",
     "sieve.bench.metrics",
     "MetricBus"
    ],
    [
     "preview_project",
     "sieve.bench.metrics",
     "Recorder"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "FrameSourceContext"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "WORKERS_OPTION"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "frame_source"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "load_project"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "lower_source_contract"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "preview_project",
     "sieve.cli.common",
     "span_for"
    ],
    [
     "preview_project",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "preview_project",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "preview_project",
     "sieve.pipeline.cache",
     "MemoryFrameStore"
    ],
    [
     "preview_project",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "preview_project",
     "sieve.pipeline.dag",
     "GraphError"
    ],
    [
     "preview_project",
     "sieve.pipeline.preview",
     "PreviewSession"
    ],
    [
     "preview_project",
     "sieve.pipeline.resolve_source",
     "resolve"
    ],
    [
     "preview_project",
     "sieve.pipeline.source_home",
     "SourceHome"
    ],
    [
     "_render",
     "sieve.backend.dispatch",
     "NoKernelError"
    ],
    [
     "_render",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_render",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "_render",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "_render",
     "sieve.pipeline.dag",
     "GraphError"
    ],
    [
     "_render",
     "sieve.pipeline.executor",
     "UnrunnableNodeError"
    ],
    [
     "_render",
     "sieve.pipeline.preview",
     "PreviewRender"
    ],
    [
     "_render",
     "sieve.pipeline.preview",
     "PreviewSession"
    ],
    [
     "_target",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_target",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_target",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_parse_edits",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_parse_edits",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_apply",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_apply",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_header",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "_header",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_header",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_header",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ],
    [
     "_describe",
     "sieve.pipeline.preview",
     "PreviewRender"
    ],
    [
     "_timings",
     "sieve.bench.budgets",
     "BUDGETS"
    ],
    [
     "_timings",
     "sieve.bench.metrics",
     "Recorder"
    ],
    [
     "_sequence",
     "sieve.bench.metrics",
     "Recorder"
    ]
   ]
  },
  "sieve.cli.run_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 305,
   "isInit": false,
   "ghost": false,
   "doc": "`sieve run` \u2014 execute a saved project through the one executor.",
   "annotation": "",
   "external": [
    "collections",
    "pathlib",
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "run_project",
     "kind": "function",
     "line": 69,
     "loc": 95,
     "doc": "Run a project's pipeline over its representative clip."
    },
    {
     "name": "_execute_all",
     "kind": "function",
     "line": 166,
     "loc": 37,
     "doc": "Run every plan against the file its replicate resolved to."
    },
    {
     "name": "_execute_one",
     "kind": "function",
     "line": 205,
     "loc": 29,
     "doc": "Run one replicate's plan and print what it did."
    },
    {
     "name": "_refuse_sinks",
     "kind": "function",
     "line": 236,
     "loc": 8,
     "doc": "Refuse a project whose declared outputs nothing can write yet."
    },
    {
     "name": "_targets",
     "kind": "function",
     "line": 246,
     "loc": 21,
     "doc": "The replicates to run, in document order, or `(None,)` for the baseline."
    },
    {
     "name": "_describe",
     "kind": "function",
     "line": 269,
     "loc": 36,
     "doc": "What `--dry-run` prints: one plan, one block."
    }
   ],
   "calls": [
    [
     "run_project",
     "_describe"
    ],
    [
     "run_project",
     "_execute_all"
    ],
    [
     "run_project",
     "_refuse_sinks"
    ],
    [
     "run_project",
     "_targets"
    ],
    [
     "_execute_all",
     "_execute_one"
    ]
   ],
   "uses": [
    [
     "run_project",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "run_project",
     "sieve.cli.common",
     "WORKERS_OPTION"
    ],
    [
     "run_project",
     "sieve.cli.common",
     "load_project"
    ],
    [
     "run_project",
     "sieve.cli.common",
     "lower_source_contract"
    ],
    [
     "run_project",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "run_project",
     "sieve.cli.common",
     "span_for"
    ],
    [
     "run_project",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "run_project",
     "sieve.pipeline.cache",
     "FrameStore"
    ],
    [
     "run_project",
     "sieve.pipeline.cache",
     "MemoryFrameStore"
    ],
    [
     "run_project",
     "sieve.pipeline.cache",
     "NullFrameStore"
    ],
    [
     "run_project",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "run_project",
     "sieve.pipeline.dag",
     "GraphError"
    ],
    [
     "run_project",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "run_project",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ],
    [
     "run_project",
     "sieve.pipeline.resolve_source",
     "resolve"
    ],
    [
     "run_project",
     "sieve.pipeline.source_home",
     "SourceHome"
    ],
    [
     "_execute_all",
     "sieve.cli.common",
     "FrameSourceContext"
    ],
    [
     "_execute_all",
     "sieve.cli.common",
     "frame_source"
    ],
    [
     "_execute_all",
     "sieve.pipeline.cache",
     "FrameStore"
    ],
    [
     "_execute_all",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_execute_all",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ],
    [
     "_execute_one",
     "sieve.backend.dispatch",
     "NoKernelError"
    ],
    [
     "_execute_one",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_execute_one",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "_execute_one",
     "sieve.pipeline.cache",
     "FrameStore"
    ],
    [
     "_execute_one",
     "sieve.pipeline.executor",
     "FrameSource"
    ],
    [
     "_execute_one",
     "sieve.pipeline.executor",
     "UnrunnableNodeError"
    ],
    [
     "_execute_one",
     "sieve.pipeline.executor",
     "execute"
    ],
    [
     "_execute_one",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_refuse_sinks",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_refuse_sinks",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_targets",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "_targets",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "_targets",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_describe",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_describe",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ]
   ]
  },
  "sieve.cli.sweep_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 153,
   "isInit": false,
   "ghost": false,
   "doc": "`sieve sweep` \u2014 decode throughput over core sets and worker counts.",
   "annotation": "",
   "external": [
    "json",
    "pathlib",
    "time",
    "typer",
    "typing"
   ],
   "symbols": [
    {
     "name": "sweep_decode",
     "kind": "function",
     "line": 54,
     "loc": 61,
     "doc": ""
    },
    {
     "name": "_integers",
     "kind": "function",
     "line": 117,
     "loc": 8,
     "doc": ""
    },
    {
     "name": "_report",
     "kind": "function",
     "line": 127,
     "loc": 26,
     "doc": ""
    }
   ],
   "calls": [
    [
     "sweep_decode",
     "_integers"
    ],
    [
     "sweep_decode",
     "_report"
    ]
   ],
   "uses": [
    [
     "sweep_decode",
     "sieve.bench.sweep",
     "AffinityUnavailableError"
    ],
    [
     "sweep_decode",
     "sieve.bench.sweep",
     "Cell"
    ],
    [
     "sweep_decode",
     "sieve.bench.sweep",
     "class_core_sets"
    ],
    [
     "sweep_decode",
     "sieve.bench.sweep",
     "design"
    ],
    [
     "sweep_decode",
     "sieve.bench.sweep",
     "sized_core_sets"
    ],
    [
     "sweep_decode",
     "sieve.bench.sweep",
     "sweep"
    ],
    [
     "sweep_decode",
     "sieve.cli.common",
     "frame_source"
    ],
    [
     "sweep_decode",
     "sieve.cli.common",
     "refuse"
    ],
    [
     "sweep_decode",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "_report",
     "sieve.bench.sweep",
     "Reading"
    ],
    [
     "_report",
     "sieve.bench.sweep",
     "curvature"
    ]
   ]
  },
  "sieve.core.__init__": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 102,
   "isInit": true,
   "ghost": false,
   "doc": "Pure logic. The bottom of the layer stack.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.core.clip_window": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 178,
   "isInit": false,
   "ghost": false,
   "doc": "What survives an edit to a `ClipRange`: its length, or one of its edges.",
   "annotation": "",
   "external": [
    "fractions"
   ],
   "symbols": [
    {
     "name": "default_window",
     "kind": "function",
     "line": 46,
     "loc": 23,
     "doc": "The window a session opens with: `seconds` of it, or all of it."
    },
    {
     "name": "effective_window",
     "kind": "function",
     "line": 71,
     "loc": 18,
     "doc": "What a session shows: the user's choice, or the default until they make one."
    },
    {
     "name": "moved_to",
     "kind": "function",
     "line": 91,
     "loc": 12,
     "doc": "`window` starting at `origin`, holding its length, clamped to the source."
    },
    {
     "name": "containing",
     "kind": "function",
     "line": 105,
     "loc": 12,
     "doc": "`window` moved the least distance that puts `frame` inside it."
    },
    {
     "name": "ended_at",
     "kind": "function",
     "line": 119,
     "loc": 14,
     "doc": "`window` ending after `frame`, inclusive of it. This is the resize."
    },
    {
     "name": "started_at",
     "kind": "function",
     "line": 135,
     "loc": 15,
     "doc": "`window` with its start dragged to `frame`, its end pinned. The left handle."
    },
    {
     "name": "ended_at_handle",
     "kind": "function",
     "line": 152,
     "loc": 12,
     "doc": "`window` with its end dragged past `frame`, its start pinned. The right handle."
    },
    {
     "name": "fitted",
     "kind": "function",
     "line": 166,
     "loc": 12,
     "doc": "A window trimmed onto a source of `frame_count` frames, or `None`."
    }
   ],
   "calls": [
    [
     "effective_window",
     "default_window"
    ],
    [
     "containing",
     "moved_to"
    ]
   ],
   "uses": [
    [
     "default_window",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "default_window",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "default_window",
     "sieve.core.types",
     "MediaTime"
    ],
    [
     "effective_window",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "moved_to",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "containing",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "ended_at",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "started_at",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "ended_at_handle",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "fitted",
     "sieve.core.pipeline_model",
     "ClipRange"
    ]
   ]
  },
  "sieve.core.filter_base": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 1119,
   "isInit": false,
   "ghost": false,
   "doc": "The filter contract, as data: `FilterSpec`, `ParamsBase`, `ArraySpec`, `Mode`.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "enum",
    "fractions",
    "json",
    "math",
    "pydantic",
    "re",
    "typing"
   ],
   "symbols": [
    {
     "name": "Mode",
     "kind": "class",
     "line": 79,
     "loc": 8,
     "doc": "Whether a filter can emit a frame as soon as it has consumed one."
    },
    {
     "name": "StreamKind",
     "kind": "class",
     "line": 89,
     "loc": 14,
     "doc": "What sort of thing travels along an edge."
    },
    {
     "name": "ElementKind",
     "kind": "class",
     "line": 105,
     "loc": 25,
     "doc": "What one value of a frame *is a value of*."
    },
    {
     "name": "ElementNames",
     "kind": "class",
     "line": 133,
     "loc": 22,
     "doc": "Column-safe names for one emitted array element."
    },
    {
     "name": "ElementRelation",
     "kind": "class",
     "line": 163,
     "loc": 23,
     "doc": "What a filter does to the element meaning it was handed."
    },
    {
     "name": "node_element",
     "kind": "function",
     "line": 197,
     "loc": 40,
     "doc": "One node's element meaning, given its input's. `None` is *undeclarable*."
    },
    {
     "name": "node_element_names",
     "kind": "function",
     "line": 239,
     "loc": 21,
     "doc": "One node's emitted element names, given its input's."
    },
    {
     "name": "ParamsBase",
     "kind": "class",
     "line": 282,
     "loc": 164,
     "doc": "Base for every filter's parameter model."
    },
    {
     "name": "ArraySpec",
     "kind": "class",
     "line": 449,
     "loc": 43,
     "doc": "What a filter consumes or produces, declared narrowly enough to reject."
    },
    {
     "name": "TableSpec",
     "kind": "class",
     "line": 495,
     "loc": 32,
     "doc": "Rows rather than frames: detections, coordinates, per-frame summaries."
    },
    {
     "name": "CostEstimate",
     "kind": "class",
     "line": 547,
     "loc": 28,
     "doc": "Order-of-magnitude cost, for predicting a run before making it."
    },
    {
     "name": "CaptionPart",
     "kind": "class",
     "line": 578,
     "loc": 13,
     "doc": "One piece of a collapsed filter caption."
    },
    {
     "name": "_empty_param_value_labels",
     "kind": "function",
     "line": 593,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "FilterSpec",
     "kind": "class",
     "line": 598,
     "loc": 295,
     "doc": "Everything about a filter that is knowable without running it."
    },
    {
     "name": "Channel",
     "kind": "class",
     "line": 895,
     "loc": 27,
     "doc": "Which of three questions a `FilterSpec` field answers."
    },
    {
     "name": "presented_param_value",
     "kind": "function",
     "line": 969,
     "loc": 16,
     "doc": "A parameter value as the filter wants it read in presentation."
    },
    {
     "name": "caption_for_params",
     "kind": "function",
     "line": 987,
     "loc": 11,
     "doc": "The declared collapsed caption for `params` under `spec`."
    },
    {
     "name": "node_warmup_frames",
     "kind": "function",
     "line": 1000,
     "loc": 39,
     "doc": "One node's own lead-in: the refinement if it has one, else the bound."
    },
    {
     "name": "input_warmup_frames",
     "kind": "function",
     "line": 1041,
     "loc": 36,
     "doc": "One node's conversion: lead-in at its input, given lead-in at its output."
    },
    {
     "name": "source_warmup_frames",
     "kind": "function",
     "line": 1079,
     "loc": 40,
     "doc": "Lead-in to decode, in *source* frames, for a path ordered root to sink."
    }
   ],
   "calls": [
    [
     "node_element",
     "ElementKind"
    ],
    [
     "node_element",
     "ElementRelation"
    ],
    [
     "node_element_names",
     "ElementKind"
    ],
    [
     "node_element_names",
     "ElementNames"
    ],
    [
     "node_element_names",
     "ElementRelation"
    ],
    [
     "ParamsBase",
     "FilterSpec"
    ],
    [
     "ArraySpec",
     "StreamKind"
    ],
    [
     "TableSpec",
     "StreamKind"
    ],
    [
     "FilterSpec",
     "ArraySpec"
    ],
    [
     "FilterSpec",
     "CaptionPart"
    ],
    [
     "FilterSpec",
     "CostEstimate"
    ],
    [
     "FilterSpec",
     "ElementKind"
    ],
    [
     "FilterSpec",
     "ElementNames"
    ],
    [
     "FilterSpec",
     "Mode"
    ],
    [
     "FilterSpec",
     "ParamsBase"
    ],
    [
     "FilterSpec",
     "_empty_param_value_labels"
    ],
    [
     "presented_param_value",
     "FilterSpec"
    ],
    [
     "presented_param_value",
     "ParamsBase"
    ],
    [
     "caption_for_params",
     "CaptionPart"
    ],
    [
     "caption_for_params",
     "FilterSpec"
    ],
    [
     "caption_for_params",
     "ParamsBase"
    ],
    [
     "caption_for_params",
     "presented_param_value"
    ],
    [
     "node_warmup_frames",
     "ParamsBase"
    ],
    [
     "input_warmup_frames",
     "node_warmup_frames"
    ],
    [
     "source_warmup_frames",
     "input_warmup_frames"
    ]
   ],
   "uses": [
    [
     "ParamsBase",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "ParamsBase",
     "sieve.core.types",
     "NO_FRAMES"
    ],
    [
     "ArraySpec",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "CostEstimate",
     "sieve.core.types",
     "WORK_UNIT_ANCHOR"
    ],
    [
     "CostEstimate",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "FilterSpec",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "FilterSpec",
     "sieve.core.types",
     "NO_FRAMES"
    ],
    [
     "node_warmup_frames",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "input_warmup_frames",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "source_warmup_frames",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "source_warmup_frames",
     "sieve.core.types",
     "NO_FRAMES"
    ]
   ]
  },
  "sieve.core.filter_registry": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 183,
   "isInit": false,
   "ghost": false,
   "doc": "The shelf filters put themselves on: a container keyed by `(id, version)`.",
   "annotation": "",
   "external": [
    "collections",
    "typing"
   ],
   "symbols": [
    {
     "name": "UnknownFilterError",
     "kind": "class",
     "line": 35,
     "loc": 2,
     "doc": "No filter is registered under the requested id or version."
    },
    {
     "name": "DuplicateFilterError",
     "kind": "class",
     "line": 39,
     "loc": 2,
     "doc": "Two filters claim the same `(filter_id, version)`."
    },
    {
     "name": "FilterRegistry",
     "kind": "class",
     "line": 43,
     "loc": 72,
     "doc": "Lookup over registered specs. Holds no kernels and executes nothing."
    },
    {
     "name": "register_filter",
     "kind": "function",
     "line": 121,
     "loc": 62,
     "doc": "Decorate a `ParamsBase` subclass to build and register its spec."
    }
   ],
   "calls": [
    [
     "FilterRegistry",
     "DuplicateFilterError"
    ],
    [
     "FilterRegistry",
     "UnknownFilterError"
    ],
    [
     "register_filter",
     "FilterRegistry"
    ]
   ],
   "uses": [
    [
     "FilterRegistry",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "ElementDeclaration"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "register_filter",
     "sieve.core.filter_base",
     "StreamSpec"
    ]
   ]
  },
  "sieve.core.history": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 220,
   "isInit": false,
   "ghost": false,
   "doc": "Automatic project history: whole documents, one per user-meaningful action.",
   "annotation": "",
   "external": [
    "dataclasses",
    "pathlib",
    "re"
   ],
   "symbols": [
    {
     "name": "slugged",
     "kind": "function",
     "line": 86,
     "loc": 11,
     "doc": "`text` reduced to the filename-safe form a snapshot is named with."
    },
    {
     "name": "Snapshot",
     "kind": "class",
     "line": 100,
     "loc": 23,
     "doc": "One written document, and what the store can say about it without reading it."
    },
    {
     "name": "SnapshotStore",
     "kind": "class",
     "line": 125,
     "loc": 90,
     "doc": "The history directory for one project, and the retention rule over it."
    },
    {
     "name": "history_directory",
     "kind": "function",
     "line": 217,
     "loc": 3,
     "doc": "Where the history for the project file at `project_path` lives."
    }
   ],
   "calls": [
    [
     "SnapshotStore",
     "Snapshot"
    ],
    [
     "SnapshotStore",
     "slugged"
    ]
   ],
   "uses": [
    [
     "SnapshotStore",
     "sieve.core.pipeline_model",
     "PROJECT_SUFFIX"
    ],
    [
     "SnapshotStore",
     "sieve.core.pipeline_model",
     "Project"
    ]
   ]
  },
  "sieve.core.ops.__init__": {
   "package": "sieve.core.ops",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 42,
   "isInit": true,
   "ghost": false,
   "doc": "Array math as a declared kind: arrays in, arrays out, no state and no spec.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.core.ops.detection": {
   "package": "sieve.core.ops",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 155,
   "isInit": false,
   "ghost": false,
   "doc": "The detection chain as pure functions: count \u2192 windowed mean \u2192 gate.",
   "annotation": "",
   "external": [
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "inband_count",
     "kind": "function",
     "line": 38,
     "loc": 10,
     "doc": "# blocks whose band power lies in ``[lo, hi]`` per frame. ``m`` is (T, B)."
    },
    {
     "name": "window_bounds",
     "kind": "function",
     "line": 50,
     "loc": 20,
     "doc": "Per-frame prefix-sum bounds ``(hi, lo, effective_length)`` for a"
    },
    {
     "name": "windowed_mean",
     "kind": "function",
     "line": 72,
     "loc": 15,
     "doc": "Centered/trailing mean of a per-frame series over ``window`` frames."
    },
    {
     "name": "settled_frames",
     "kind": "function",
     "line": 89,
     "loc": 20,
     "doc": "How many leading frames of a *truncated* series already have their final"
    },
    {
     "name": "count_band_to_counts",
     "kind": "function",
     "line": 111,
     "loc": 16,
     "doc": "The one place a fractional count band becomes block counts."
    },
    {
     "name": "detect_gate",
     "kind": "function",
     "line": 129,
     "loc": 10,
     "doc": "Positive detection per frame: windowed in-band count within ``[lo, hi]``."
    },
    {
     "name": "gate_intervals",
     "kind": "function",
     "line": 141,
     "loc": 14,
     "doc": "Contiguous ``[start, end)`` frame runs where the gate is on."
    }
   ],
   "calls": [
    [
     "windowed_mean",
     "window_bounds"
    ]
   ],
   "uses": []
  },
  "sieve.core.ops.wavelet": {
   "package": "sieve.core.ops",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 355,
   "isInit": false,
   "ghost": false,
   "doc": "Morlet continuous wavelet transform for per-block signal series.",
   "annotation": "",
   "external": [
    "concurrent",
    "numpy",
    "scipy",
    "typing"
   ],
   "symbols": [
    {
     "name": "_pool_size",
     "kind": "function",
     "line": 56,
     "loc": 15,
     "doc": "`workers` as a `ThreadPoolExecutor` size; `None` is the stdlib default."
    },
    {
     "name": "_fast_len",
     "kind": "function",
     "line": 76,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "_fft_time_axis",
     "kind": "function",
     "line": 82,
     "loc": 5,
     "doc": ""
    },
    {
     "name": "_ifft_time_axis",
     "kind": "function",
     "line": 89,
     "loc": 5,
     "doc": ""
    },
    {
     "name": "morlet_scales",
     "kind": "function",
     "line": 96,
     "loc": 4,
     "doc": "Wavelet scale ``s`` for each desired Fourier frequency (w0=6 Morlet)."
    },
    {
     "name": "coi_efolding_s",
     "kind": "function",
     "line": 102,
     "loc": 18,
     "doc": "Cone-of-influence half-width in *seconds* for each Fourier frequency."
    },
    {
     "name": "coi_edge_samples",
     "kind": "function",
     "line": 122,
     "loc": 4,
     "doc": "`coi_efolding_s` in samples at rate ``fs`` \u2014 the form a plot with a"
    },
    {
     "name": "settled_frames",
     "kind": "function",
     "line": 173,
     "loc": 31,
     "doc": "How many leading frames of a *truncated* record already have their final"
    },
    {
     "name": "default_freqs",
     "kind": "function",
     "line": 206,
     "loc": 3,
     "doc": "Log-spaced frequency bank, capped below Nyquist (0.45 \u00b7 fps)."
    },
    {
     "name": "morlet_power",
     "kind": "function",
     "line": 211,
     "loc": 35,
     "doc": "Morlet scalogram power. ``x`` (T,) or (T, B) \u2192 (F, T) or (F, T, B) float32."
    },
    {
     "name": "_daughter",
     "kind": "function",
     "line": 248,
     "loc": 6,
     "doc": "One scale's frequency-domain Morlet daughter, T&C-normalized."
    },
    {
     "name": "band_indices",
     "kind": "function",
     "line": 256,
     "loc": 17,
     "doc": "Frequency rows ``[i, j)`` covering ``[flo, fhi]`` Hz on a sorted bank."
    },
    {
     "name": "morlet_band_power",
     "kind": "function",
     "line": 275,
     "loc": 80,
     "doc": "Scalogram power summed over frequency rows ``[i, j)``. ``x`` (T,) or"
    }
   ],
   "calls": [
    [
     "coi_efolding_s",
     "morlet_scales"
    ],
    [
     "coi_edge_samples",
     "coi_efolding_s"
    ],
    [
     "settled_frames",
     "coi_edge_samples"
    ],
    [
     "morlet_power",
     "_daughter"
    ],
    [
     "morlet_power",
     "_fast_len"
    ],
    [
     "morlet_power",
     "_fft_time_axis"
    ],
    [
     "morlet_power",
     "_ifft_time_axis"
    ],
    [
     "morlet_power",
     "coi_efolding_s"
    ],
    [
     "morlet_power",
     "morlet_scales"
    ],
    [
     "morlet_band_power",
     "_daughter"
    ],
    [
     "morlet_band_power",
     "_fast_len"
    ],
    [
     "morlet_band_power",
     "_fft_time_axis"
    ],
    [
     "morlet_band_power",
     "_ifft_time_axis"
    ],
    [
     "morlet_band_power",
     "_pool_size"
    ],
    [
     "morlet_band_power",
     "coi_efolding_s"
    ],
    [
     "morlet_band_power",
     "morlet_scales"
    ]
   ],
   "uses": []
  },
  "sieve.core.pipeline_model": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 1274,
   "isInit": false,
   "ghost": false,
   "doc": "The pipeline artifact: the serialized form a run is reproducible from.",
   "annotation": "",
   "external": [
    "collections",
    "json",
    "math",
    "os",
    "pathlib",
    "pydantic",
    "typing",
    "uuid",
    "yaml"
   ],
   "symbols": [
    {
     "name": "project_path_for",
     "kind": "function",
     "line": 147,
     "loc": 6,
     "doc": "Where the project file for `video` belongs."
    },
    {
     "name": "as_project_path",
     "kind": "function",
     "line": 155,
     "loc": 14,
     "doc": "`path` renamed to end in `.sieve.yaml`, for a caller handed a typed name."
    },
    {
     "name": "_new_id",
     "kind": "function",
     "line": 171,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "_resolved",
     "kind": "function",
     "line": 175,
     "loc": 10,
     "doc": "Absolute, `..` collapsed, symlinks followed."
    },
    {
     "name": "_posix_relative",
     "kind": "function",
     "line": 187,
     "loc": 12,
     "doc": "`target` as a POSIX path relative to `base`, or absolute if it cannot be."
    },
    {
     "name": "_Artifact",
     "kind": "class",
     "line": 201,
     "loc": 20,
     "doc": "Shared config for every model in the artifact."
    },
    {
     "name": "SourceRef",
     "kind": "class",
     "line": 223,
     "loc": 31,
     "doc": "The video a project is about, named relative to the project file."
    },
    {
     "name": "ClipRange",
     "kind": "class",
     "line": 256,
     "loc": 28,
     "doc": "The representative five to ten seconds the user tunes against."
    },
    {
     "name": "DetectorSettings",
     "kind": "class",
     "line": 286,
     "loc": 55,
     "doc": "The detection suffix's tuned values: bands, count threshold, window D."
    },
    {
     "name": "resolved_detector",
     "kind": "function",
     "line": 343,
     "loc": 22,
     "doc": "The detector values `replicate` actually runs with."
    },
    {
     "name": "Node",
     "kind": "class",
     "line": 367,
     "loc": 44,
     "doc": "One filter application, named but not resolved."
    },
    {
     "name": "resolved_params",
     "kind": "function",
     "line": 413,
     "loc": 20,
     "doc": "The parameters `node` actually runs with, for `replicate`."
    },
    {
     "name": "edited_params",
     "kind": "function",
     "line": 435,
     "loc": 22,
     "doc": "One parameter edit's two writes: the pin, and the moved default."
    },
    {
     "name": "edited_detector",
     "kind": "function",
     "line": 459,
     "loc": 16,
     "doc": "`edited_params` for the detector: pin the diff, move the baseline."
    },
    {
     "name": "Edge",
     "kind": "class",
     "line": 477,
     "loc": 31,
     "doc": "`upstream`'s output feeds one of `downstream`'s input ports."
    },
    {
     "name": "Sink",
     "kind": "class",
     "line": 510,
     "loc": 50,
     "doc": "A declared output: VISION step 6's \"select a specific stage to output\"."
    },
    {
     "name": "CropArtifact",
     "kind": "class",
     "line": 570,
     "loc": 100,
     "doc": "One replicate's crop, written to a file that is then a source in itself."
    },
    {
     "name": "Pipeline",
     "kind": "class",
     "line": 672,
     "loc": 58,
     "doc": "The graph itself: no source video, no replicates, no output locations."
    },
    {
     "name": "_params_fingerprint",
     "kind": "function",
     "line": 732,
     "loc": 32,
     "doc": "Canonical text standing for everything `replicate` runs the graph with."
    },
    {
     "name": "equivalence_groups",
     "kind": "function",
     "line": 766,
     "loc": 48,
     "doc": "Group number per replicate, positionally, counting from 1."
    },
    {
     "name": "Project",
     "kind": "class",
     "line": 816,
     "loc": 458,
     "doc": "A source video, how it is cut, what runs on it, and what comes out."
    }
   ],
   "calls": [
    [
     "_posix_relative",
     "_resolved"
    ],
    [
     "SourceRef",
     "_Artifact"
    ],
    [
     "SourceRef",
     "_posix_relative"
    ],
    [
     "SourceRef",
     "_resolved"
    ],
    [
     "ClipRange",
     "_Artifact"
    ],
    [
     "DetectorSettings",
     "_Artifact"
    ],
    [
     "resolved_detector",
     "DetectorSettings"
    ],
    [
     "Node",
     "_Artifact"
    ],
    [
     "Node",
     "_new_id"
    ],
    [
     "resolved_params",
     "Node"
    ],
    [
     "edited_params",
     "Node"
    ],
    [
     "edited_params",
     "resolved_params"
    ],
    [
     "edited_detector",
     "DetectorSettings"
    ],
    [
     "edited_detector",
     "resolved_detector"
    ],
    [
     "Edge",
     "_Artifact"
    ],
    [
     "Sink",
     "_Artifact"
    ],
    [
     "Sink",
     "_new_id"
    ],
    [
     "Sink",
     "_resolved"
    ],
    [
     "CropArtifact",
     "ClipRange"
    ],
    [
     "CropArtifact",
     "_Artifact"
    ],
    [
     "CropArtifact",
     "_resolved"
    ],
    [
     "Pipeline",
     "Edge"
    ],
    [
     "Pipeline",
     "Node"
    ],
    [
     "Pipeline",
     "_Artifact"
    ],
    [
     "_params_fingerprint",
     "DetectorSettings"
    ],
    [
     "_params_fingerprint",
     "Node"
    ],
    [
     "_params_fingerprint",
     "resolved_detector"
    ],
    [
     "_params_fingerprint",
     "resolved_params"
    ],
    [
     "equivalence_groups",
     "DetectorSettings"
    ],
    [
     "equivalence_groups",
     "Pipeline"
    ],
    [
     "equivalence_groups",
     "_params_fingerprint"
    ],
    [
     "Project",
     "ClipRange"
    ],
    [
     "Project",
     "CropArtifact"
    ],
    [
     "Project",
     "DetectorSettings"
    ],
    [
     "Project",
     "Node"
    ],
    [
     "Project",
     "Pipeline"
    ],
    [
     "Project",
     "Sink"
    ],
    [
     "Project",
     "SourceRef"
    ],
    [
     "Project",
     "_Artifact"
    ],
    [
     "Project",
     "_posix_relative"
    ],
    [
     "Project",
     "edited_detector"
    ],
    [
     "Project",
     "edited_params"
    ],
    [
     "Project",
     "equivalence_groups"
    ],
    [
     "Project",
     "resolved_detector"
    ],
    [
     "Project",
     "resolved_params"
    ]
   ],
   "uses": [
    [
     "resolved_detector",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "Node",
     "sieve.core.filter_base",
     "FILTER_ID_PATTERN"
    ],
    [
     "Node",
     "sieve.core.filter_base",
     "SEMVER_PATTERN"
    ],
    [
     "resolved_params",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "edited_params",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "edited_detector",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "Edge",
     "sieve.core.filter_base",
     "DEFAULT_PORT"
    ],
    [
     "Edge",
     "sieve.core.filter_base",
     "PORT_PATTERN"
    ],
    [
     "CropArtifact",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "CropArtifact",
     "sieve.core.types",
     "ROI"
    ],
    [
     "_params_fingerprint",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "equivalence_groups",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "Project",
     "sieve.core.replicates",
     "Replicate"
    ]
   ]
  },
  "sieve.core.replicates": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 233,
   "isInit": false,
   "ghost": false,
   "doc": "The replicate document: an ordered set of named regions cut from one source.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "re",
    "typing",
    "uuid"
   ],
   "symbols": [
    {
     "name": "_new_id",
     "kind": "function",
     "line": 37,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "_no_overrides",
     "kind": "function",
     "line": 41,
     "loc": 3,
     "doc": "An empty deviation map, typed \u2014 `default_factory=dict` infers nothing."
    },
    {
     "name": "_no_detector_overrides",
     "kind": "function",
     "line": 46,
     "loc": 3,
     "doc": "An empty detector deviation, typed for the same reason."
    },
    {
     "name": "Replicate",
     "kind": "class",
     "line": 52,
     "loc": 108,
     "doc": "A named region of the source, stable across renames and geometry edits."
    },
    {
     "name": "ReplicateSet",
     "kind": "class",
     "line": 162,
     "loc": 71,
     "doc": "Ordered, mutable collection of replicates addressed by position."
    }
   ],
   "calls": [
    [
     "Replicate",
     "_new_id"
    ],
    [
     "Replicate",
     "_no_detector_overrides"
    ],
    [
     "Replicate",
     "_no_overrides"
    ],
    [
     "ReplicateSet",
     "Replicate"
    ]
   ],
   "uses": [
    [
     "Replicate",
     "sieve.core.types",
     "ROI"
    ]
   ]
  },
  "sieve.core.request_intent": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 75,
   "isInit": false,
   "ghost": false,
   "doc": "Why a frame was asked for, and what that entitles it to.",
   "annotation": "",
   "external": [
    "enum"
   ],
   "symbols": [
    {
     "name": "RequestKind",
     "kind": "class",
     "line": 26,
     "loc": 49,
     "doc": "Why a frame was asked for."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.core.types": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 626,
   "isInit": false,
   "ghost": false,
   "doc": "Frame, ROI, quantities, and metadata value objects shared across all layers.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "enum",
    "fractions",
    "math",
    "numpy",
    "pathlib",
    "typing"
   ],
   "symbols": [
    {
     "name": "MediaTime",
     "kind": "class",
     "line": 61,
     "loc": 42,
     "doc": "A position or a length on the *media* clock, exactly."
    },
    {
     "name": "WallTime",
     "kind": "class",
     "line": 106,
     "loc": 41,
     "doc": "Elapsed real time \u2014 what a budget bounds and a stopwatch reports."
    },
    {
     "name": "WorkUnits",
     "kind": "class",
     "line": 150,
     "loc": 30,
     "doc": "An amount of work, denominated against an anchor and not against a clock."
    },
    {
     "name": "FrameCount",
     "kind": "class",
     "line": 196,
     "loc": 65,
     "doc": "A number of frames in one node's index space. Never a duration."
    },
    {
     "name": "FrameIndex",
     "kind": "class",
     "line": 270,
     "loc": 70,
     "doc": "A source-frame position, not a count of frames."
    },
    {
     "name": "FrameRange",
     "kind": "class",
     "line": 343,
     "loc": 33,
     "doc": "A half-open source-frame range whose iteration yields `FrameIndex`."
    },
    {
     "name": "ChannelSpec",
     "kind": "class",
     "line": 378,
     "loc": 15,
     "doc": "How the trailing axis of a frame's array is laid out."
    },
    {
     "name": "ROI",
     "kind": "class",
     "line": 396,
     "loc": 119,
     "doc": "An axis-aligned region in integer pixels of the array it indexes."
    },
    {
     "name": "VideoMetadata",
     "kind": "class",
     "line": 518,
     "loc": 26,
     "doc": "Everything known about a source video without decoding its content."
    },
    {
     "name": "Frame",
     "kind": "class",
     "line": 547,
     "loc": 30,
     "doc": "One decoded frame plus the identity needed to reason about it."
    },
    {
     "name": "FrameSpan",
     "kind": "class",
     "line": 580,
     "loc": 46,
     "doc": "A consecutive, non-empty run of frames handed to a windowed kernel."
    }
   ],
   "calls": [
    [
     "MediaTime",
     "FrameCount"
    ],
    [
     "FrameCount",
     "MediaTime"
    ],
    [
     "FrameIndex",
     "FrameCount"
    ],
    [
     "FrameRange",
     "FrameIndex"
    ],
    [
     "VideoMetadata",
     "FrameCount"
    ],
    [
     "VideoMetadata",
     "FrameIndex"
    ],
    [
     "VideoMetadata",
     "MediaTime"
    ],
    [
     "Frame",
     "ChannelSpec"
    ],
    [
     "Frame",
     "FrameIndex"
    ],
    [
     "FrameSpan",
     "Frame"
    ],
    [
     "FrameSpan",
     "FrameCount"
    ],
    [
     "FrameSpan",
     "FrameIndex"
    ]
   ],
   "uses": []
  },
  "sieve.decode.__init__": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 7,
   "isInit": true,
   "ghost": false,
   "doc": "Video decode. The only place OpenCV is allowed to appear.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.decode.ffmpeg": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 275,
   "isInit": false,
   "ghost": false,
   "doc": "FFmpeg rawvideo source for a crop/scale prefix lowered out of the graph.",
   "annotation": "",
   "external": [
    "fractions",
    "functools",
    "numpy",
    "pathlib",
    "subprocess",
    "types",
    "typing"
   ],
   "symbols": [
    {
     "name": "FfmpegUnavailableError",
     "kind": "class",
     "line": 27,
     "loc": 2,
     "doc": "The FFmpeg executable needed for the lowered source is not usable."
    },
    {
     "name": "resolve_ffmpeg_workers",
     "kind": "function",
     "line": 31,
     "loc": 5,
     "doc": "Threads the FFmpeg subprocess may use."
    },
    {
     "name": "ffmpeg_decoder_identity",
     "kind": "function",
     "line": 39,
     "loc": 21,
     "doc": "The FFmpeg build that owns lowered-source pixels."
    },
    {
     "name": "ffmpeg_lowered_command",
     "kind": "function",
     "line": 62,
     "loc": 37,
     "doc": "Command that emits gray8 working-size frames from `start_index` onward."
    },
    {
     "name": "FfmpegLoweredFrameSource",
     "kind": "class",
     "line": 101,
     "loc": 139,
     "doc": "A `FrameSource` backed by one FFmpeg rawvideo pipe."
    },
    {
     "name": "_metadata",
     "kind": "function",
     "line": 242,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "_check_prefix_fits",
     "kind": "function",
     "line": 247,
     "loc": 7,
     "doc": ""
    },
    {
     "name": "_timestamp",
     "kind": "function",
     "line": 256,
     "loc": 5,
     "doc": ""
    },
    {
     "name": "_gray_frame",
     "kind": "function",
     "line": 263,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "_stderr_text",
     "kind": "function",
     "line": 267,
     "loc": 8,
     "doc": ""
    }
   ],
   "calls": [
    [
     "ffmpeg_decoder_identity",
     "FfmpegUnavailableError"
    ],
    [
     "ffmpeg_lowered_command",
     "_timestamp"
    ],
    [
     "FfmpegLoweredFrameSource",
     "FfmpegUnavailableError"
    ],
    [
     "FfmpegLoweredFrameSource",
     "_check_prefix_fits"
    ],
    [
     "FfmpegLoweredFrameSource",
     "_gray_frame"
    ],
    [
     "FfmpegLoweredFrameSource",
     "_metadata"
    ],
    [
     "FfmpegLoweredFrameSource",
     "_stderr_text"
    ],
    [
     "FfmpegLoweredFrameSource",
     "ffmpeg_lowered_command"
    ],
    [
     "FfmpegLoweredFrameSource",
     "resolve_ffmpeg_workers"
    ]
   ],
   "uses": [
    [
     "FfmpegUnavailableError",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "resolve_ffmpeg_workers",
     "sieve.mutual.machine",
     "available_cpus"
    ],
    [
     "ffmpeg_decoder_identity",
     "sieve.decode.lowered",
     "LOWERED_SOURCE_POLICY_VERSION"
    ],
    [
     "ffmpeg_lowered_command",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "ffmpeg_lowered_command",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.core.types",
     "Frame"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "FfmpegLoweredFrameSource",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "_metadata",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "_metadata",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "_check_prefix_fits",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "_check_prefix_fits",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "_check_prefix_fits",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "_timestamp",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "_timestamp",
     "sieve.decode.reader",
     "VideoDecodeError"
    ]
   ]
  },
  "sieve.decode.identity": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 34,
   "isInit": false,
   "ghost": false,
   "doc": "Decoder identity string for cache key derivation.",
   "annotation": "",
   "external": [
    "cv2",
    "functools"
   ],
   "symbols": [
    {
     "name": "decoder_identity",
     "kind": "function",
     "line": 32,
     "loc": 2,
     "doc": ""
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.decode.lowered": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 113,
   "isInit": false,
   "ghost": false,
   "doc": "Pure value objects for source prefixes that have been lowered into decode.",
   "annotation": "",
   "external": [
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "roi_parts",
     "kind": "function",
     "line": 21,
     "loc": 3,
     "doc": "`roi` in the only order FFmpeg and the cache key both use."
    },
    {
     "name": "LoweredStep",
     "kind": "class",
     "line": 27,
     "loc": 9,
     "doc": "One declared operation that was removed from the executor's DAG."
    },
    {
     "name": "LoweredScale",
     "kind": "class",
     "line": 39,
     "loc": 17,
     "doc": "The one spatial scale operation FFmpeg will apply."
    },
    {
     "name": "LoweredPrefix",
     "kind": "class",
     "line": 59,
     "loc": 54,
     "doc": "The source-side crop and scale now owned by the decoder route."
    }
   ],
   "calls": [
    [
     "LoweredPrefix",
     "LoweredScale"
    ],
    [
     "LoweredPrefix",
     "LoweredStep"
    ],
    [
     "LoweredPrefix",
     "roi_parts"
    ]
   ],
   "uses": [
    [
     "roi_parts",
     "sieve.core.types",
     "ROI"
    ],
    [
     "LoweredPrefix",
     "sieve.core.types",
     "ROI"
    ]
   ]
  },
  "sieve.decode.prefetch": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 453,
   "isInit": false,
   "ghost": false,
   "doc": "N readers over one file, reading ahead in order, so the convert is not the rate.",
   "annotation": "",
   "external": [
    "pathlib",
    "threading",
    "types",
    "typing"
   ],
   "symbols": [
    {
     "name": "resolve_workers",
     "kind": "function",
     "line": 136,
     "loc": 35,
     "doc": "How many decode threads to run: the request, else what the machine allows."
    },
    {
     "name": "PrefetchFrameSource",
     "kind": "class",
     "line": 173,
     "loc": 280,
     "doc": "A `FrameSource` that decodes ahead of the caller on `workers` threads."
    }
   ],
   "calls": [
    [
     "PrefetchFrameSource",
     "resolve_workers"
    ]
   ],
   "uses": [
    [
     "resolve_workers",
     "sieve.mutual.machine",
     "available_cpus"
    ],
    [
     "PrefetchFrameSource",
     "sieve.core.types",
     "Frame"
    ],
    [
     "PrefetchFrameSource",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "PrefetchFrameSource",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "PrefetchFrameSource",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "PrefetchFrameSource",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "PrefetchFrameSource",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ]
   ]
  },
  "sieve.decode.quiet": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 157,
   "isInit": false,
   "ghost": false,
   "doc": "Drop one known-benign OpenCV line from stderr, and pass everything else on.",
   "annotation": "",
   "external": [
    "atexit",
    "contextlib",
    "io",
    "os",
    "re",
    "sys",
    "threading"
   ],
   "symbols": [
    {
     "name": "silence_raw_format_warning",
     "kind": "function",
     "line": 64,
     "loc": 55,
     "doc": "Start filtering `_RAW_FORMAT_LINE` out of this process's stderr."
    },
    {
     "name": "_pump",
     "kind": "function",
     "line": 121,
     "loc": 15,
     "doc": "Forward stderr line by line, dropping the one known line."
    },
    {
     "name": "_restore",
     "kind": "function",
     "line": 138,
     "loc": 19,
     "doc": "Put the real stderr back, and let the pump drain before the process goes."
    }
   ],
   "calls": [
    [
     "silence_raw_format_warning",
     "_pump"
    ],
    [
     "silence_raw_format_warning",
     "_restore"
    ]
   ],
   "uses": []
  },
  "sieve.decode.reader": {
   "package": "sieve.decode",
   "layerPackage": "sieve.decode",
   "band": 4,
   "loc": 210,
   "isInit": false,
   "ghost": false,
   "doc": "OpenCV `VideoCapture` wrapper trading grab-vs-seek and BGR-vs-luma for",
   "annotation": "",
   "external": [
    "av",
    "cv2",
    "fractions",
    "numpy",
    "pathlib",
    "types",
    "typing"
   ],
   "symbols": [
    {
     "name": "VideoDecodeError",
     "kind": "class",
     "line": 48,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "container_rate",
     "kind": "function",
     "line": 52,
     "loc": 30,
     "doc": "The frame rate the container declares, as the rational it declares it as."
    },
    {
     "name": "VideoReader",
     "kind": "class",
     "line": 86,
     "loc": 115,
     "doc": ""
    },
    {
     "name": "_downscale",
     "kind": "function",
     "line": 203,
     "loc": 7,
     "doc": ""
    }
   ],
   "calls": [
    [
     "VideoReader",
     "VideoDecodeError"
    ],
    [
     "VideoReader",
     "_downscale"
    ],
    [
     "VideoReader",
     "container_rate"
    ]
   ],
   "uses": [
    [
     "VideoReader",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "VideoReader",
     "sieve.core.types",
     "Frame"
    ],
    [
     "VideoReader",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "VideoReader",
     "sieve.core.types",
     "VideoMetadata"
    ]
   ]
  },
  "sieve.detect.__init__": {
   "package": "sieve.detect",
   "layerPackage": "sieve.detect",
   "band": 4,
   "loc": 26,
   "isInit": true,
   "ghost": false,
   "doc": "Detection over an extracted series, below both front ends.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.detect.detector": {
   "package": "sieve.detect",
   "layerPackage": "sieve.detect",
   "band": 4,
   "loc": 166,
   "isInit": false,
   "ghost": false,
   "doc": "Bands, threshold, and window composed into intervals. Qt-free, front-end-free.",
   "annotation": "",
   "external": [
    "dataclasses",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "DetectorUpdate",
     "kind": "class",
     "line": 48,
     "loc": 17,
     "doc": "One pure derivation over one collected series."
    },
    {
     "name": "detect",
     "kind": "function",
     "line": 67,
     "loc": 55,
     "doc": "The whole derivation `DetectorSettings` names, over one series."
    },
    {
     "name": "settled_for",
     "kind": "function",
     "line": 124,
     "loc": 21,
     "doc": "Where a record of `frames` stops being provisional, under `settings`."
    },
    {
     "name": "gate_to",
     "kind": "function",
     "line": 147,
     "loc": 19,
     "doc": "Truncate the gate and its intervals to the settled frontier."
    }
   ],
   "calls": [
    [
     "detect",
     "DetectorUpdate"
    ],
    [
     "gate_to",
     "DetectorUpdate"
    ]
   ],
   "uses": [
    [
     "detect",
     "sieve.core.ops.detection",
     "count_band_to_counts"
    ],
    [
     "detect",
     "sieve.core.ops.detection",
     "detect_gate"
    ],
    [
     "detect",
     "sieve.core.ops.detection",
     "gate_intervals"
    ],
    [
     "detect",
     "sieve.core.ops.detection",
     "inband_count"
    ],
    [
     "detect",
     "sieve.core.ops.detection",
     "windowed_mean"
    ],
    [
     "detect",
     "sieve.core.ops.wavelet",
     "band_indices"
    ],
    [
     "detect",
     "sieve.core.ops.wavelet",
     "default_freqs"
    ],
    [
     "detect",
     "sieve.core.ops.wavelet",
     "morlet_band_power"
    ],
    [
     "detect",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "settled_for",
     "sieve.core.ops.detection",
     "settled_frames"
    ],
    [
     "settled_for",
     "sieve.core.ops.wavelet",
     "band_indices"
    ],
    [
     "settled_for",
     "sieve.core.ops.wavelet",
     "default_freqs"
    ],
    [
     "settled_for",
     "sieve.core.ops.wavelet",
     "settled_frames"
    ],
    [
     "settled_for",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "gate_to",
     "sieve.core.ops.detection",
     "gate_intervals"
    ]
   ]
  },
  "sieve.detect.tables": {
   "package": "sieve.detect",
   "layerPackage": "sieve.detect",
   "band": 4,
   "loc": 588,
   "isInit": false,
   "ghost": false,
   "doc": "A detection written where R can read it, and a person can too.",
   "annotation": "",
   "external": [
    "collections",
    "csv",
    "dataclasses",
    "fractions",
    "math",
    "numpy",
    "pathlib",
    "typing"
   ],
   "symbols": [
    {
     "name": "Column",
     "kind": "class",
     "line": 101,
     "loc": 20,
     "doc": "A column's name, what it means, and how to get it \u2014 declared once."
    },
    {
     "name": "TableVerificationError",
     "kind": "class",
     "line": 136,
     "loc": 2,
     "doc": "The written table did not read back as the rows that were handed to it."
    },
    {
     "name": "DetectionExport",
     "kind": "class",
     "line": 141,
     "loc": 22,
     "doc": "One replicate's detection, and what is needed to say where it came from."
    },
    {
     "name": "Frame",
     "kind": "class",
     "line": 166,
     "loc": 19,
     "doc": "One row of `series.csv`: a replicate's detection, at one offset into it."
    },
    {
     "name": "Interval",
     "kind": "class",
     "line": 188,
     "loc": 6,
     "doc": "One row of `intervals.csv`, half-open in frames as the gate holds it."
    },
    {
     "name": "series_columns",
     "kind": "function",
     "line": 196,
     "loc": 65,
     "doc": "`series.csv`'s columns, four of them named for what was counted."
    },
    {
     "name": "series_column_names",
     "kind": "function",
     "line": 263,
     "loc": 7,
     "doc": "The header names generated for `element_names`."
    },
    {
     "name": "element_series_column_names",
     "kind": "function",
     "line": 272,
     "loc": 9,
     "doc": "The series columns whose names depend on the emitted element noun."
    },
    {
     "name": "write_tables",
     "kind": "function",
     "line": 314,
     "loc": 37,
     "doc": "Write `series.csv`, `README.md`, and `intervals.csv` when armed."
    },
    {
     "name": "_series_rows",
     "kind": "function",
     "line": 353,
     "loc": 6,
     "doc": ""
    },
    {
     "name": "_interval_rows",
     "kind": "function",
     "line": 361,
     "loc": 12,
     "doc": "Every armed replicate's intervals, in the order the gate found them."
    },
    {
     "name": "_detected",
     "kind": "function",
     "line": 375,
     "loc": 11,
     "doc": "`TRUE`/`FALSE` \u2014 R's own spelling, which pandas also reads as boolean."
    },
    {
     "name": "_measured",
     "kind": "function",
     "line": 388,
     "loc": 13,
     "doc": "A `float32` array element, at the shortest length that round-trips it."
    },
    {
     "name": "_fraction",
     "kind": "function",
     "line": 403,
     "loc": 13,
     "doc": "`value / elements` \u2014 the scale `DetectorSettings.count_frac` is stated in."
    },
    {
     "name": "_at_frame",
     "kind": "function",
     "line": 418,
     "loc": 14,
     "doc": "How long `frames` of the source last, to `SECONDS_DECIMALS`."
    },
    {
     "name": "_seconds",
     "kind": "function",
     "line": 434,
     "loc": 14,
     "doc": "A media time as fixed-point seconds, rounded in exact arithmetic."
    },
    {
     "name": "_nonfinite",
     "kind": "function",
     "line": 450,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "_band",
     "kind": "function",
     "line": 456,
     "loc": 15,
     "doc": "A `[lo, hi]` band in prose, with an open end said rather than printed."
    },
    {
     "name": "_dictionary",
     "kind": "function",
     "line": 473,
     "loc": 8,
     "doc": "The markdown table for `columns` \u2014 rendered from them, never beside them."
    },
    {
     "name": "_readme",
     "kind": "function",
     "line": 483,
     "loc": 63,
     "doc": "A data dictionary, and the settings the columns cannot carry."
    },
    {
     "name": "write_table",
     "kind": "function",
     "line": 548,
     "loc": 30,
     "doc": "One verified CSV: write, read back, then rename \u2014 `materialize.py`'s order."
    },
    {
     "name": "_verify",
     "kind": "function",
     "line": 580,
     "loc": 8,
     "doc": ""
    }
   ],
   "calls": [
    [
     "Frame",
     "DetectionExport"
    ],
    [
     "Interval",
     "DetectionExport"
    ],
    [
     "series_columns",
     "Column"
    ],
    [
     "series_columns",
     "Frame"
    ],
    [
     "series_columns",
     "_at_frame"
    ],
    [
     "series_columns",
     "_detected"
    ],
    [
     "series_columns",
     "_fraction"
    ],
    [
     "series_columns",
     "_measured"
    ],
    [
     "series_column_names",
     "series_columns"
    ],
    [
     "write_tables",
     "DetectionExport"
    ],
    [
     "write_tables",
     "_interval_rows"
    ],
    [
     "write_tables",
     "_readme"
    ],
    [
     "write_tables",
     "_series_rows"
    ],
    [
     "write_tables",
     "series_columns"
    ],
    [
     "write_tables",
     "write_table"
    ],
    [
     "_series_rows",
     "DetectionExport"
    ],
    [
     "_series_rows",
     "Frame"
    ],
    [
     "_interval_rows",
     "DetectionExport"
    ],
    [
     "_interval_rows",
     "Interval"
    ],
    [
     "_detected",
     "Frame"
    ],
    [
     "_measured",
     "_nonfinite"
    ],
    [
     "_fraction",
     "_nonfinite"
    ],
    [
     "_at_frame",
     "DetectionExport"
    ],
    [
     "_at_frame",
     "_seconds"
    ],
    [
     "_dictionary",
     "Column"
    ],
    [
     "_readme",
     "Column"
    ],
    [
     "_readme",
     "DetectionExport"
    ],
    [
     "_readme",
     "Frame"
    ],
    [
     "_readme",
     "_band"
    ],
    [
     "_readme",
     "_dictionary"
    ],
    [
     "write_table",
     "Column"
    ],
    [
     "write_table",
     "_verify"
    ],
    [
     "_verify",
     "TableVerificationError"
    ]
   ],
   "uses": [
    [
     "DetectionExport",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "DetectionExport",
     "sieve.detect.detector",
     "DetectorUpdate"
    ],
    [
     "series_columns",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "series_column_names",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "element_series_column_names",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "write_tables",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "_at_frame",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "_at_frame",
     "sieve.core.types",
     "MediaTime"
    ],
    [
     "_seconds",
     "sieve.core.types",
     "MediaTime"
    ],
    [
     "_readme",
     "sieve.core.filter_base",
     "ElementNames"
    ]
   ]
  },
  "sieve.filters.__init__": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 158,
   "isInit": true,
   "ghost": false,
   "doc": "Every filter, found by scanning this package rather than by listing it.",
   "annotation": "",
   "external": [
    "dataclasses",
    "importlib",
    "pathlib",
    "pkgutil",
    "sys"
   ],
   "symbols": [
    {
     "name": "discover",
     "kind": "function",
     "line": 45,
     "loc": 24,
     "doc": "Import every filter module, then return what is on the shelf."
    },
    {
     "name": "guidance_path",
     "kind": "function",
     "line": 71,
     "loc": 25,
     "doc": "Where `spec`'s guidance markdown lives, whether or not it is there."
    },
    {
     "name": "Guidance",
     "kind": "class",
     "line": 106,
     "loc": 12,
     "doc": "A filter's markdown split into the sections above, plus its one-liner."
    },
    {
     "name": "parse_guidance",
     "kind": "function",
     "line": 120,
     "loc": 20,
     "doc": "`## ` sections of a guidance file, header \u2192 body, reading order."
    },
    {
     "name": "guidance_for",
     "kind": "function",
     "line": 142,
     "loc": 16,
     "doc": "`spec`'s guidance, degrading to its summary when the file cannot be read."
    }
   ],
   "calls": [
    [
     "guidance_for",
     "Guidance"
    ],
    [
     "guidance_for",
     "guidance_path"
    ],
    [
     "guidance_for",
     "parse_guidance"
    ]
   ],
   "uses": [
    [
     "discover",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "discover",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "guidance_path",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "guidance_for",
     "sieve.core.filter_base",
     "FilterSpec"
    ]
   ]
  },
  "sieve.filters.background_ema": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 338,
   "isInit": false,
   "ghost": false,
   "doc": "An exponential moving-average background model, and the difference from it.",
   "annotation": "",
   "external": [
    "dataclasses",
    "enum",
    "math",
    "numpy",
    "pydantic",
    "typing"
   ],
   "symbols": [
    {
     "name": "settle_frames",
     "kind": "function",
     "line": 96,
     "loc": 19,
     "doc": "Frames until the seed frame holds less than `epsilon` of the model."
    },
    {
     "name": "Emit",
     "kind": "class",
     "line": 117,
     "loc": 9,
     "doc": "Which of the two things this filter has computed leaves the node."
    },
    {
     "name": "BackgroundEmaParams",
     "kind": "class",
     "line": 163,
     "loc": 27,
     "doc": "How fast the background forgets, and which half of the result to emit."
    },
    {
     "name": "_Buffers",
     "kind": "class",
     "line": 200,
     "loc": 18,
     "doc": "The three full-frame arrays one run reuses, allocated once."
    },
    {
     "name": "BackgroundState",
     "kind": "class",
     "line": 221,
     "loc": 43,
     "doc": "One run's model and its working arrays. Made by `KernelBinding.start`."
    },
    {
     "name": "background_ema_cpu",
     "kind": "function",
     "line": 267,
     "loc": 48,
     "doc": "Update the model with this frame, then emit the requested half."
    },
    {
     "name": "_narrow",
     "kind": "function",
     "line": 317,
     "loc": 21,
     "doc": "Return `values` as `dtype`, rounding rather than truncating for integers."
    }
   ],
   "calls": [
    [
     "BackgroundEmaParams",
     "Emit"
    ],
    [
     "BackgroundEmaParams",
     "settle_frames"
    ],
    [
     "BackgroundState",
     "_Buffers"
    ],
    [
     "background_ema_cpu",
     "BackgroundEmaParams"
    ],
    [
     "background_ema_cpu",
     "BackgroundState"
    ],
    [
     "background_ema_cpu",
     "Emit"
    ],
    [
     "background_ema_cpu",
     "_narrow"
    ]
   ],
   "uses": [
    [
     "BackgroundEmaParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "BackgroundEmaParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "BackgroundState",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "background_ema_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "background_ema_cpu",
     "sieve.backend.dispatch",
     "stateful_kernel"
    ],
    [
     "background_ema_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.block_signal": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 449,
   "isInit": false,
   "ghost": false,
   "doc": "Per-block motion signals from the structure tensor of consecutive frames.",
   "annotation": "",
   "external": [
    "cv2",
    "dataclasses",
    "enum",
    "numpy",
    "pydantic",
    "typing"
   ],
   "symbols": [
    {
     "name": "auto_block",
     "kind": "function",
     "line": 100,
     "loc": 8,
     "doc": "The `0 = auto` block size in working pixels: 64 source px at `scale`."
    },
    {
     "name": "resolve_block",
     "kind": "function",
     "line": 110,
     "loc": 3,
     "doc": "Effective block size in working pixels: explicit, or auto from scale."
    },
    {
     "name": "grid_shape",
     "kind": "function",
     "line": 115,
     "loc": 8,
     "doc": "The `(ny, nx)` block grid for a working frame \u2014 ceiling division."
    },
    {
     "name": "Signal",
     "kind": "class",
     "line": 125,
     "loc": 13,
     "doc": "Which read of the structure tensor leaves the node."
    },
    {
     "name": "BlockSignalParams",
     "kind": "class",
     "line": 178,
     "loc": 30,
     "doc": "Which signal, on what grid, at what time scale."
    },
    {
     "name": "BlockSignalState",
     "kind": "class",
     "line": 211,
     "loc": 4,
     "doc": "The previous preprocessed gray frame. `None` until the first frame."
    },
    {
     "name": "block_signal_cpu",
     "kind": "function",
     "line": 218,
     "loc": 36,
     "doc": "Measure this frame against the previous one, then remember it."
    },
    {
     "name": "_to_gray",
     "kind": "function",
     "line": 256,
     "loc": 12,
     "doc": "The frame as float32 gray, whatever came in."
    },
    {
     "name": "_blur",
     "kind": "function",
     "line": 270,
     "loc": 4,
     "doc": "One tensor product, spatially windowed. The cast contains cv2's"
    },
    {
     "name": "_lk_flow",
     "kind": "function",
     "line": 276,
     "loc": 31,
     "doc": "Per-pixel LK flow `(u, v)` and the mask of pixels that resolved it."
    },
    {
     "name": "_flow_speed",
     "kind": "function",
     "line": 309,
     "loc": 4,
     "doc": "Per-pixel LK speed in px/s. Zero exactly where the solve was degenerate."
    },
    {
     "name": "_flow_agreement",
     "kind": "function",
     "line": 315,
     "loc": 34,
     "doc": "Resultant length of the block's unit flow vectors, in [0, 1]."
    },
    {
     "name": "_coherence",
     "kind": "function",
     "line": 351,
     "loc": 49,
     "doc": "Spatial coherency of the block-reduced 3D structure tensor, in [0, 1]."
    },
    {
     "name": "_block_mean",
     "kind": "function",
     "line": 402,
     "loc": 35,
     "doc": "Block-mean with partial edge blocks averaged over their true pixels."
    },
    {
     "name": "_block_mean_nan_padded",
     "kind": "function",
     "line": 439,
     "loc": 10,
     "doc": ""
    }
   ],
   "calls": [
    [
     "resolve_block",
     "auto_block"
    ],
    [
     "BlockSignalParams",
     "Signal"
    ],
    [
     "BlockSignalParams",
     "resolve_block"
    ],
    [
     "block_signal_cpu",
     "BlockSignalParams"
    ],
    [
     "block_signal_cpu",
     "BlockSignalState"
    ],
    [
     "block_signal_cpu",
     "Signal"
    ],
    [
     "block_signal_cpu",
     "_block_mean"
    ],
    [
     "block_signal_cpu",
     "_blur"
    ],
    [
     "block_signal_cpu",
     "_coherence"
    ],
    [
     "block_signal_cpu",
     "_flow_agreement"
    ],
    [
     "block_signal_cpu",
     "_flow_speed"
    ],
    [
     "block_signal_cpu",
     "_to_gray"
    ],
    [
     "block_signal_cpu",
     "grid_shape"
    ],
    [
     "block_signal_cpu",
     "resolve_block"
    ],
    [
     "_lk_flow",
     "_blur"
    ],
    [
     "_flow_speed",
     "_lk_flow"
    ],
    [
     "_flow_agreement",
     "_block_mean"
    ],
    [
     "_flow_agreement",
     "_lk_flow"
    ],
    [
     "_coherence",
     "_block_mean"
    ],
    [
     "_coherence",
     "_blur"
    ],
    [
     "_block_mean",
     "_block_mean_nan_padded"
    ]
   ],
   "uses": [
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "ElementKind"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "BlockSignalParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "BlockSignalParams",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "BlockSignalParams",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "BlockSignalParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "block_signal_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "block_signal_cpu",
     "sieve.backend.dispatch",
     "stateful_kernel"
    ],
    [
     "block_signal_cpu",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "block_signal_cpu",
     "sieve.core.types",
     "Frame"
    ],
    [
     "_to_gray",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "_to_gray",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.crop": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 124,
   "isInit": false,
   "ghost": false,
   "doc": "Take a region of every frame, with the whole frame as the identity value.",
   "annotation": "",
   "external": [
    "numpy"
   ],
   "symbols": [
    {
     "name": "CropParams",
     "kind": "class",
     "line": 91,
     "loc": 15,
     "doc": "Which region of the input frame survives."
    },
    {
     "name": "crop_cpu",
     "kind": "function",
     "line": 109,
     "loc": 15,
     "doc": "The region of `frame` this node declares, trimmed to what arrived."
    }
   ],
   "calls": [
    [
     "crop_cpu",
     "CropParams"
    ]
   ],
   "uses": [
    [
     "CropParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "CropParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "CropParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "CropParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "CropParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "CropParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "CropParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "CropParams",
     "sieve.core.types",
     "ROI"
    ],
    [
     "CropParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "crop_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "crop_cpu",
     "sieve.backend.dispatch",
     "kernel"
    ],
    [
     "crop_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.detect": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 227,
   "isInit": false,
   "ghost": false,
   "doc": "Detection as a discovered windowed filter.",
   "annotation": "",
   "external": [
    "math",
    "numpy",
    "pydantic",
    "typing"
   ],
   "symbols": [
    {
     "name": "_wavelet_warmup_frames",
     "kind": "function",
     "line": 58,
     "loc": 8,
     "doc": "History needed to keep the target out of the wavelet's padded edge."
    },
    {
     "name": "DetectParams",
     "kind": "class",
     "line": 99,
     "loc": 45,
     "doc": "The detector's identity parameters, plus source fps for the wavelet bank."
    },
    {
     "name": "detect_series",
     "kind": "function",
     "line": 146,
     "loc": 25,
     "doc": "Derive the detector over a whole collected series through filter params."
    },
    {
     "name": "pooled_scalogram",
     "kind": "function",
     "line": 173,
     "loc": 10,
     "doc": "The pooled Morlet surface the GUI plots beside the detector output."
    },
    {
     "name": "settled_for",
     "kind": "function",
     "line": 185,
     "loc": 3,
     "doc": "The safe detection frontier for `params` over `frames` collected rows."
    },
    {
     "name": "gate_to",
     "kind": "function",
     "line": 190,
     "loc": 3,
     "doc": "Truncate a gate through the filter-owned compatibility boundary."
    },
    {
     "name": "detect_cpu",
     "kind": "function",
     "line": 196,
     "loc": 22,
     "doc": "Emit the target frame's gate as a scalar channel."
    },
    {
     "name": "_series2d",
     "kind": "function",
     "line": 220,
     "loc": 7,
     "doc": ""
    }
   ],
   "calls": [
    [
     "DetectParams",
     "_wavelet_warmup_frames"
    ],
    [
     "detect_series",
     "DetectParams"
    ],
    [
     "detect_series",
     "_series2d"
    ],
    [
     "pooled_scalogram",
     "DetectParams"
    ],
    [
     "pooled_scalogram",
     "_series2d"
    ],
    [
     "settled_for",
     "DetectParams"
    ],
    [
     "detect_cpu",
     "DetectParams"
    ],
    [
     "detect_cpu",
     "detect_series"
    ]
   ],
   "uses": [
    [
     "_wavelet_warmup_frames",
     "sieve.core.ops.wavelet",
     "PAD_EFOLDINGS"
    ],
    [
     "_wavelet_warmup_frames",
     "sieve.core.ops.wavelet",
     "band_indices"
    ],
    [
     "_wavelet_warmup_frames",
     "sieve.core.ops.wavelet",
     "coi_edge_samples"
    ],
    [
     "_wavelet_warmup_frames",
     "sieve.core.ops.wavelet",
     "default_freqs"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "ElementKind"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "DetectParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "DetectParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "DetectParams",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "DetectParams",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "DetectParams",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "DetectParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "detect_series",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "detect_series",
     "sieve.detect.detector",
     "DetectorUpdate"
    ],
    [
     "detect_series",
     "sieve.detect.detector",
     "detect"
    ],
    [
     "pooled_scalogram",
     "sieve.core.ops.wavelet",
     "default_freqs"
    ],
    [
     "pooled_scalogram",
     "sieve.core.ops.wavelet",
     "morlet_power"
    ],
    [
     "settled_for",
     "sieve.detect.detector",
     "settled_for"
    ],
    [
     "gate_to",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "gate_to",
     "sieve.detect.detector",
     "DetectorUpdate"
    ],
    [
     "gate_to",
     "sieve.detect.detector",
     "gate_to"
    ],
    [
     "detect_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "detect_cpu",
     "sieve.backend.dispatch",
     "windowed_kernel"
    ],
    [
     "detect_cpu",
     "sieve.core.ops.wavelet",
     "ALL_CORES"
    ],
    [
     "detect_cpu",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "detect_cpu",
     "sieve.core.types",
     "Frame"
    ],
    [
     "detect_cpu",
     "sieve.core.types",
     "FrameSpan"
    ]
   ]
  },
  "sieve.filters.downsample": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 128,
   "isInit": false,
   "ghost": false,
   "doc": "Reduce spatial resolution by an integer factor.",
   "annotation": "",
   "external": [
    "cv2",
    "numpy",
    "pydantic"
   ],
   "symbols": [
    {
     "name": "DownsampleParams",
     "kind": "class",
     "line": 69,
     "loc": 24,
     "doc": "How far to reduce, and whether to average or to sample."
    },
    {
     "name": "downsample_cpu",
     "kind": "function",
     "line": 96,
     "loc": 32,
     "doc": "Downsample on the host."
    }
   ],
   "calls": [
    [
     "downsample_cpu",
     "DownsampleParams"
    ]
   ],
   "uses": [
    [
     "DownsampleParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "DownsampleParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "DownsampleParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "DownsampleParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "DownsampleParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "DownsampleParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "DownsampleParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "DownsampleParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "downsample_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "downsample_cpu",
     "sieve.backend.dispatch",
     "kernel"
    ],
    [
     "downsample_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.motion_history": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 238,
   "isInit": false,
   "ghost": false,
   "doc": "A causal leaky accumulator over per-block activity, with neighbourhood",
   "annotation": "",
   "external": [
    "dataclasses",
    "enum",
    "math",
    "numpy",
    "pydantic",
    "typing"
   ],
   "symbols": [
    {
     "name": "decay_lambda",
     "kind": "function",
     "line": 74,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "settle_frames",
     "kind": "function",
     "line": 79,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "group_delay",
     "kind": "function",
     "line": 83,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "diffusion_number",
     "kind": "function",
     "line": 88,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "diffusion_substeps",
     "kind": "function",
     "line": 92,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "coupling_weight",
     "kind": "function",
     "line": 97,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "dilate_radius",
     "kind": "function",
     "line": 103,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "Couple",
     "kind": "class",
     "line": 109,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "MotionHistoryParams",
     "kind": "class",
     "line": 139,
     "loc": 19,
     "doc": ""
    },
    {
     "name": "MotionHistoryState",
     "kind": "class",
     "line": 161,
     "loc": 21,
     "doc": ""
    },
    {
     "name": "motion_history_cpu",
     "kind": "function",
     "line": 185,
     "loc": 12,
     "doc": ""
    },
    {
     "name": "_couple",
     "kind": "function",
     "line": 199,
     "loc": 10,
     "doc": ""
    },
    {
     "name": "_diffuse",
     "kind": "function",
     "line": 211,
     "loc": 10,
     "doc": ""
    },
    {
     "name": "_dilate",
     "kind": "function",
     "line": 223,
     "loc": 15,
     "doc": ""
    }
   ],
   "calls": [
    [
     "settle_frames",
     "decay_lambda"
    ],
    [
     "group_delay",
     "decay_lambda"
    ],
    [
     "diffusion_substeps",
     "diffusion_number"
    ],
    [
     "MotionHistoryParams",
     "Couple"
    ],
    [
     "MotionHistoryParams",
     "group_delay"
    ],
    [
     "MotionHistoryParams",
     "settle_frames"
    ],
    [
     "motion_history_cpu",
     "MotionHistoryParams"
    ],
    [
     "motion_history_cpu",
     "MotionHistoryState"
    ],
    [
     "motion_history_cpu",
     "_couple"
    ],
    [
     "motion_history_cpu",
     "decay_lambda"
    ],
    [
     "_couple",
     "Couple"
    ],
    [
     "_couple",
     "MotionHistoryParams"
    ],
    [
     "_couple",
     "_diffuse"
    ],
    [
     "_couple",
     "_dilate"
    ],
    [
     "_couple",
     "coupling_weight"
    ],
    [
     "_couple",
     "dilate_radius"
    ],
    [
     "_diffuse",
     "MotionHistoryParams"
    ],
    [
     "_diffuse",
     "diffusion_number"
    ],
    [
     "_diffuse",
     "diffusion_substeps"
    ]
   ],
   "uses": [
    [
     "MotionHistoryParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "MotionHistoryParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "MotionHistoryState",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "motion_history_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "motion_history_cpu",
     "sieve.backend.dispatch",
     "stateful_kernel"
    ],
    [
     "motion_history_cpu",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "motion_history_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.normalize": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 139,
   "isInit": false,
   "ghost": false,
   "doc": "Per-frame contrast normalization: `off` or `zscore`.",
   "annotation": "",
   "external": [
    "cv2",
    "enum",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "NormalizeMode",
     "kind": "class",
     "line": 62,
     "loc": 5,
     "doc": "Whether to touch the pixels at all."
    },
    {
     "name": "NormalizeParams",
     "kind": "class",
     "line": 91,
     "loc": 4,
     "doc": "Which normalization, if any."
    },
    {
     "name": "normalize_cpu",
     "kind": "function",
     "line": 98,
     "loc": 23,
     "doc": "Normalize per-frame global statistics to mean 128, sd 32."
    },
    {
     "name": "_gray_stats",
     "kind": "function",
     "line": 123,
     "loc": 16,
     "doc": "Mean and std of the frame's gray projection (see module docstring)."
    }
   ],
   "calls": [
    [
     "NormalizeParams",
     "NormalizeMode"
    ],
    [
     "normalize_cpu",
     "NormalizeMode"
    ],
    [
     "normalize_cpu",
     "NormalizeParams"
    ],
    [
     "normalize_cpu",
     "_gray_stats"
    ]
   ],
   "uses": [
    [
     "NormalizeParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "NormalizeParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "NormalizeParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "NormalizeParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "NormalizeParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "NormalizeParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "NormalizeParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "NormalizeParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "normalize_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "normalize_cpu",
     "sieve.backend.dispatch",
     "kernel"
    ],
    [
     "normalize_cpu",
     "sieve.core.types",
     "Frame"
    ],
    [
     "_gray_stats",
     "sieve.core.types",
     "ChannelSpec"
    ]
   ]
  },
  "sieve.filters.rescale": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 105,
   "isInit": false,
   "ghost": false,
   "doc": "Reduce spatial resolution by a float linear scale factor.",
   "annotation": "",
   "external": [
    "cv2",
    "pydantic"
   ],
   "symbols": [
    {
     "name": "RescaleParams",
     "kind": "class",
     "line": 67,
     "loc": 16,
     "doc": "How far to shrink, as a linear factor of both extents."
    },
    {
     "name": "rescale_cpu",
     "kind": "function",
     "line": 86,
     "loc": 19,
     "doc": "Shrink on the host, or hand the frame through untouched at 1.0."
    }
   ],
   "calls": [
    [
     "rescale_cpu",
     "RescaleParams"
    ]
   ],
   "uses": [
    [
     "RescaleParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "RescaleParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "RescaleParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "RescaleParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "RescaleParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "RescaleParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "RescaleParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "RescaleParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "rescale_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "rescale_cpu",
     "sieve.backend.dispatch",
     "kernel"
    ],
    [
     "rescale_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.span": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 144,
   "isInit": false,
   "ghost": false,
   "doc": "Keep a range of frames, with every frame there could be as the identity value.",
   "annotation": "",
   "external": [
    "pydantic",
    "typing"
   ],
   "symbols": [
    {
     "name": "SpanParams",
     "kind": "class",
     "line": 93,
     "loc": 38,
     "doc": "Which frames survive, half-open, in source indices."
    },
    {
     "name": "span_cpu",
     "kind": "function",
     "line": 134,
     "loc": 10,
     "doc": "`frame`, unchanged."
    }
   ],
   "calls": [
    [
     "span_cpu",
     "SpanParams"
    ]
   ],
   "uses": [
    [
     "SpanParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "SpanParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "SpanParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "SpanParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "SpanParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "SpanParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "SpanParams",
     "sieve.core.filter_base",
     "UNBOUNDED_FRAME"
    ],
    [
     "SpanParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "SpanParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "span_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "span_cpu",
     "sieve.backend.dispatch",
     "kernel"
    ],
    [
     "span_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.filters.temporal_baseline": {
   "package": "sieve.filters",
   "layerPackage": "sieve.filters",
   "band": 3,
   "loc": 374,
   "isInit": false,
   "ghost": false,
   "doc": "Each cell's own null distribution over time, and the signal in units of it.",
   "annotation": "",
   "external": [
    "dataclasses",
    "enum",
    "math",
    "numpy",
    "pydantic",
    "typing"
   ],
   "symbols": [
    {
     "name": "window_frames",
     "kind": "function",
     "line": 121,
     "loc": 8,
     "doc": "The trailing window in frames \u2014 at least one."
    },
    {
     "name": "sample_stride",
     "kind": "function",
     "line": 131,
     "loc": 7,
     "doc": "Frames between admissions, so the ring spans `frames` in `MAX_SAMPLES`."
    },
    {
     "name": "ring_capacity",
     "kind": "function",
     "line": 140,
     "loc": 4,
     "doc": "Samples held for a window of `frames`. Never above `MAX_SAMPLES`."
    },
    {
     "name": "Emit",
     "kind": "class",
     "line": 146,
     "loc": 11,
     "doc": "Which of the two things this filter has computed leaves the node."
    },
    {
     "name": "TemporalBaselineParams",
     "kind": "class",
     "line": 194,
     "loc": 33,
     "doc": "How long the null is estimated over, and which half of the result to emit."
    },
    {
     "name": "BaselineState",
     "kind": "class",
     "line": 230,
     "loc": 54,
     "doc": "One run's ring of samples and the estimate derived from it."
    },
    {
     "name": "temporal_baseline_cpu",
     "kind": "function",
     "line": 287,
     "loc": 46,
     "doc": "Admit this frame if the stride says so, then measure it against the ring."
    },
    {
     "name": "_estimate",
     "kind": "function",
     "line": 335,
     "loc": 16,
     "doc": "Per-cell median and sigma-equivalent spread over the samples held."
    },
    {
     "name": "_floored",
     "kind": "function",
     "line": 353,
     "loc": 21,
     "doc": "Replace a cell's zero spread with the median of the frame's nonzero ones."
    }
   ],
   "calls": [
    [
     "ring_capacity",
     "sample_stride"
    ],
    [
     "TemporalBaselineParams",
     "Emit"
    ],
    [
     "TemporalBaselineParams",
     "window_frames"
    ],
    [
     "temporal_baseline_cpu",
     "BaselineState"
    ],
    [
     "temporal_baseline_cpu",
     "Emit"
    ],
    [
     "temporal_baseline_cpu",
     "TemporalBaselineParams"
    ],
    [
     "temporal_baseline_cpu",
     "_estimate"
    ],
    [
     "temporal_baseline_cpu",
     "ring_capacity"
    ],
    [
     "temporal_baseline_cpu",
     "sample_stride"
    ],
    [
     "_estimate",
     "BaselineState"
    ],
    [
     "_estimate",
     "_floored"
    ]
   ],
   "uses": [
    [
     "TemporalBaselineParams",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.filter_base",
     "CaptionPart"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.filter_base",
     "CostEstimate"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.filter_base",
     "ElementRelation"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.filter_registry",
     "register_filter"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "TemporalBaselineParams",
     "sieve.core.types",
     "WorkUnits"
    ],
    [
     "BaselineState",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "temporal_baseline_cpu",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "temporal_baseline_cpu",
     "sieve.backend.dispatch",
     "stateful_kernel"
    ],
    [
     "temporal_baseline_cpu",
     "sieve.core.types",
     "Frame"
    ]
   ]
  },
  "sieve.gui.__init__": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 7,
   "isInit": true,
   "ghost": false,
   "doc": "Desktop application.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.gui.__main__": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 7,
   "isInit": false,
   "ghost": false,
   "doc": "`python -m sieve.gui`.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.gui.app": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 57,
   "isInit": false,
   "ghost": false,
   "doc": "The one place that mutates process-wide state before any window exists,",
   "annotation": "",
   "external": [
    "PySide6",
    "pathlib",
    "sys"
   ],
   "symbols": [
    {
     "name": "main",
     "kind": "function",
     "line": 32,
     "loc": 21,
     "doc": ""
    }
   ],
   "calls": [],
   "uses": [
    [
     "main",
     "sieve.__init__",
     "__version__"
    ],
    [
     "main",
     "sieve.decode.quiet",
     "silence_raw_format_warning"
    ],
    [
     "main",
     "sieve.gui.keyboard_handback",
     "KeyboardHandback"
    ],
    [
     "main",
     "sieve.gui.main_window",
     "MainWindow"
    ],
    [
     "main",
     "sieve.gui.wheel_steps",
     "WheelSteps"
    ]
   ]
  },
  "sieve.gui.band_plot": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 503,
   "isInit": false,
   "ghost": false,
   "doc": "The shared frame of the detection plots: axes, handles, and the gesture.",
   "annotation": "",
   "external": [
    "PySide6",
    "math",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "plot_font",
     "kind": "function",
     "line": 89,
     "loc": 8,
     "doc": "The plots' one font, at `size` points."
    },
    {
     "name": "ramp_lut",
     "kind": "function",
     "line": 99,
     "loc": 14,
     "doc": "A 256-entry ARGB32 lookup table interpolating `stops` dark \u2192 light."
    },
    {
     "name": "argb_to_qimage",
     "kind": "function",
     "line": 115,
     "loc": 5,
     "doc": "An owning QImage of an (H, W) ARGB32 array (`.copy()` \u2014 the array may go)."
    },
    {
     "name": "BandPlot",
     "kind": "class",
     "line": 122,
     "loc": 381,
     "doc": "The shared frame: title row, grid, playhead, gate underpaint, two handles."
    }
   ],
   "calls": [
    [
     "BandPlot",
     "plot_font"
    ]
   ],
   "uses": []
  },
  "sieve.gui.block_spin": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 51,
   "isInit": false,
   "ghost": false,
   "doc": "The Block spin box: a size, a mode below it, and no refusal between them.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "BlockSpinBox",
     "kind": "class",
     "line": 33,
     "loc": 18,
     "doc": ""
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.chain_model": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 448,
   "isInit": false,
   "ghost": false,
   "doc": "The live tab's chain and detector, as Qt-free state the stack renders.",
   "annotation": "",
   "external": [
    "dataclasses",
    "enum",
    "itertools",
    "math",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "ChainKind",
     "kind": "class",
     "line": 61,
     "loc": 11,
     "doc": "What travels between two steps, at the granularity the stack grades."
    },
    {
     "name": "Stage",
     "kind": "class",
     "line": 74,
     "loc": 7,
     "doc": "The fixed headers the stack groups cards under, in chain order."
    },
    {
     "name": "Status",
     "kind": "class",
     "line": 83,
     "loc": 6,
     "doc": "One step's grade."
    },
    {
     "name": "ChainStep",
     "kind": "class",
     "line": 92,
     "loc": 15,
     "doc": "One card of the stack."
    },
    {
     "name": "StepGrade",
     "kind": "class",
     "line": 110,
     "loc": 8,
     "doc": "One step's status, with the conflict spelled out for its card."
    },
    {
     "name": "grade",
     "kind": "function",
     "line": 120,
     "loc": 27,
     "doc": "Every step's status, for a chain in any state at all."
    },
    {
     "name": "runnable_prefix",
     "kind": "function",
     "line": 149,
     "loc": 17,
     "doc": "The `Pipeline` value of the ok node-backed prefix, edges included."
    },
    {
     "name": "DetectorState",
     "kind": "class",
     "line": 169,
     "loc": 78,
     "doc": "The tab-side suffix's parameters: bands, window, arming, solo."
    },
    {
     "name": "recompute",
     "kind": "function",
     "line": 249,
     "loc": 24,
     "doc": "The detect filter's series adapter with the live state converted at the boundary."
    },
    {
     "name": "snapped_band_label",
     "kind": "function",
     "line": 275,
     "loc": 11,
     "doc": "The *snapped* frequency band, as the scalogram title and caption render it."
    },
    {
     "name": "caption_for",
     "kind": "function",
     "line": 288,
     "loc": 27,
     "doc": "One line restating the step's current values."
    },
    {
     "name": "_threshold_caption",
     "kind": "function",
     "line": 317,
     "loc": 10,
     "doc": "The count threshold in words, fraction-denominated like the state."
    },
    {
     "name": "LiveChain",
     "kind": "class",
     "line": 342,
     "loc": 50,
     "doc": "The whole tab-side model: steps plus detector, one value."
    },
    {
     "name": "parity_chain",
     "kind": "function",
     "line": 394,
     "loc": 54,
     "doc": "The tab's default chain: the five parity steps, default knobs, disarmed."
    }
   ],
   "calls": [
    [
     "ChainStep",
     "ChainKind"
    ],
    [
     "ChainStep",
     "Stage"
    ],
    [
     "StepGrade",
     "Status"
    ],
    [
     "grade",
     "ChainKind"
    ],
    [
     "grade",
     "ChainStep"
    ],
    [
     "grade",
     "Status"
    ],
    [
     "grade",
     "StepGrade"
    ],
    [
     "runnable_prefix",
     "ChainStep"
    ],
    [
     "runnable_prefix",
     "Status"
    ],
    [
     "runnable_prefix",
     "grade"
    ],
    [
     "recompute",
     "DetectorState"
    ],
    [
     "caption_for",
     "ChainStep"
    ],
    [
     "caption_for",
     "DetectorState"
    ],
    [
     "caption_for",
     "Stage"
    ],
    [
     "caption_for",
     "_threshold_caption"
    ],
    [
     "caption_for",
     "snapped_band_label"
    ],
    [
     "_threshold_caption",
     "DetectorState"
    ],
    [
     "LiveChain",
     "ChainStep"
    ],
    [
     "LiveChain",
     "DetectorState"
    ],
    [
     "LiveChain",
     "Stage"
    ],
    [
     "LiveChain",
     "Status"
    ],
    [
     "LiveChain",
     "StepGrade"
    ],
    [
     "LiveChain",
     "grade"
    ],
    [
     "LiveChain",
     "runnable_prefix"
    ],
    [
     "parity_chain",
     "ChainKind"
    ],
    [
     "parity_chain",
     "ChainStep"
    ],
    [
     "parity_chain",
     "DetectorState"
    ],
    [
     "parity_chain",
     "LiveChain"
    ],
    [
     "parity_chain",
     "Stage"
    ]
   ],
   "uses": [
    [
     "ChainStep",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "runnable_prefix",
     "sieve.core.pipeline_model",
     "Edge"
    ],
    [
     "runnable_prefix",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "runnable_prefix",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "DetectorState",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "recompute",
     "sieve.filters.detect",
     "DetectParams"
    ],
    [
     "recompute",
     "sieve.filters.detect",
     "DetectorUpdate"
    ],
    [
     "recompute",
     "sieve.filters.detect",
     "detect"
    ],
    [
     "snapped_band_label",
     "sieve.core.ops.wavelet",
     "band_indices"
    ],
    [
     "snapped_band_label",
     "sieve.core.ops.wavelet",
     "default_freqs"
    ],
    [
     "caption_for",
     "sieve.core.filter_base",
     "caption_for_params"
    ],
    [
     "caption_for",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "caption_for",
     "sieve.core.filter_registry",
     "UnknownFilterError"
    ],
    [
     "caption_for",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "LiveChain",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "parity_chain",
     "sieve.core.pipeline_model",
     "Node"
    ]
   ]
  },
  "sieve.gui.chain_stack": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 602,
   "isInit": false,
   "ghost": false,
   "doc": "The operation stack: the live chain as cards under fixed stage headers.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections"
   ],
   "symbols": [
    {
     "name": "SeamStrip",
     "kind": "class",
     "line": 78,
     "loc": 40,
     "doc": "One seam between cards: invisible until hovered, then hairline + plus."
    },
    {
     "name": "StageHeader",
     "kind": "class",
     "line": 120,
     "loc": 17,
     "doc": "A fixed stage title with its `in \u2192 out` type chip."
    },
    {
     "name": "StepCard",
     "kind": "class",
     "line": 139,
     "loc": 155,
     "doc": "One step: painted header (title, caption, status) over borrowed bodies."
    },
    {
     "name": "SourceCard",
     "kind": "class",
     "line": 324,
     "loc": 136,
     "doc": "What the chain consumes, and whether it is at rest."
    },
    {
     "name": "ChainStackView",
     "kind": "class",
     "line": 462,
     "loc": 140,
     "doc": "The right column: Reset above the scrolling column of seams and cards."
    }
   ],
   "calls": [
    [
     "ChainStackView",
     "SeamStrip"
    ],
    [
     "ChainStackView",
     "SourceCard"
    ],
    [
     "ChainStackView",
     "StageHeader"
    ],
    [
     "ChainStackView",
     "StepCard"
    ]
   ],
   "uses": [
    [
     "SeamStrip",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "StageHeader",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "StageHeader",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "StageHeader",
     "sieve.gui.chain_model",
     "STAGE_CHIPS"
    ],
    [
     "StageHeader",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "StepCard",
     "sieve.gui.band_plot",
     "ACCENT"
    ],
    [
     "StepCard",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "StepCard",
     "sieve.gui.band_plot",
     "LINE"
    ],
    [
     "StepCard",
     "sieve.gui.band_plot",
     "PANEL"
    ],
    [
     "StepCard",
     "sieve.gui.band_plot",
     "TEXT"
    ],
    [
     "StepCard",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "StepCard",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "StepCard",
     "sieve.gui.chain_model",
     "Status"
    ],
    [
     "StepCard",
     "sieve.gui.chain_model",
     "StepGrade"
    ],
    [
     "SourceCard",
     "sieve.gui.band_plot",
     "ACCENT"
    ],
    [
     "SourceCard",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "SourceCard",
     "sieve.gui.band_plot",
     "LINE"
    ],
    [
     "SourceCard",
     "sieve.gui.band_plot",
     "PANEL"
    ],
    [
     "SourceCard",
     "sieve.gui.band_plot",
     "TEXT"
    ],
    [
     "SourceCard",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "SourceCard",
     "sieve.pipeline.crop_binding",
     "CropState"
    ],
    [
     "ChainStackView",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "ChainStackView",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "ChainStackView",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "ChainStackView",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "ChainStackView",
     "sieve.gui.chain_model",
     "Status"
    ],
    [
     "ChainStackView",
     "sieve.gui.chain_model",
     "StepGrade"
    ]
   ]
  },
  "sieve.gui.commands": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 435,
   "isInit": false,
   "ghost": false,
   "doc": "Undo commands over the replicate document.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections",
    "dataclasses",
    "typing"
   ],
   "symbols": [
    {
     "name": "AddReplicate",
     "kind": "class",
     "line": 35,
     "loc": 16,
     "doc": "Insert a replicate at a known position."
    },
    {
     "name": "RemoveReplicate",
     "kind": "class",
     "line": 53,
     "loc": 17,
     "doc": "Delete a replicate, remembering it for undo."
    },
    {
     "name": "RenameReplicate",
     "kind": "class",
     "line": 72,
     "loc": 20,
     "doc": "Change a replicate's display name."
    },
    {
     "name": "SetReplicateROI",
     "kind": "class",
     "line": 99,
     "loc": 77,
     "doc": "Change a replicate's geometry, optionally as one step of a live drag."
    },
    {
     "name": "SetReplicateROIs",
     "kind": "class",
     "line": 178,
     "loc": 35,
     "doc": "Give several replicates new geometry as a single undo entry."
    },
    {
     "name": "EditTuningParams",
     "kind": "class",
     "line": 215,
     "loc": 47,
     "doc": "Rewrite node baselines, pinning what changed on one replicate."
    },
    {
     "name": "EditDetector",
     "kind": "class",
     "line": 269,
     "loc": 60,
     "doc": "Move the detector baseline, pinning what changed on one replicate."
    },
    {
     "name": "ResetTuning",
     "kind": "class",
     "line": 331,
     "loc": 43,
     "doc": "Return every baseline to its defaults and drop every pin, everywhere."
    },
    {
     "name": "SetClip",
     "kind": "class",
     "line": 376,
     "loc": 28,
     "doc": "Move, place, or drop the representative clip."
    },
    {
     "name": "RestoreSnapshot",
     "kind": "class",
     "line": 406,
     "loc": 29,
     "doc": "Roll the whole document back to a state autosave wrote earlier."
    }
   ],
   "calls": [],
   "uses": [
    [
     "AddReplicate",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "AddReplicate",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "RemoveReplicate",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "RemoveReplicate",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "RenameReplicate",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "RenameReplicate",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "SetReplicateROI",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "SetReplicateROI",
     "sieve.core.types",
     "ROI"
    ],
    [
     "SetReplicateROI",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "SetReplicateROIs",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "SetReplicateROIs",
     "sieve.core.types",
     "ROI"
    ],
    [
     "SetReplicateROIs",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "EditTuningParams",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "EditTuningParams",
     "sieve.core.pipeline_model",
     "edited_params"
    ],
    [
     "EditTuningParams",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "EditTuningParams",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "EditDetector",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "EditDetector",
     "sieve.core.pipeline_model",
     "edited_detector"
    ],
    [
     "EditDetector",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "EditDetector",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "ResetTuning",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "ResetTuning",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "ResetTuning",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "ResetTuning",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "SetClip",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "SetClip",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "RestoreSnapshot",
     "sieve.gui.document",
     "DocumentState"
    ],
    [
     "RestoreSnapshot",
     "sieve.gui.document",
     "ReplicateDocument"
    ]
   ]
  },
  "sieve.gui.commit_combo": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 96,
   "isInit": false,
   "ghost": false,
   "doc": "A drop menu whose value changes when the user says it does.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "CommitCombo",
     "kind": "class",
     "line": 55,
     "loc": 41,
     "doc": "A `QComboBox` that has a highlight state distinct from its selection."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.composite_view": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 817,
   "isInit": false,
   "ghost": false,
   "doc": "The step composite: the selected step's output over that step's input.",
   "annotation": "",
   "external": [
    "PySide6",
    "bisect",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "_cell_span",
     "kind": "function",
     "line": 154,
     "loc": 5,
     "doc": "The inclusive range of cells whose pixels intersect `low..high`."
    },
    {
     "name": "_CompositePane",
     "kind": "class",
     "line": 161,
     "loc": 374,
     "doc": "The paint surface: base full, over at the owner's opacity, grid on top."
    },
    {
     "name": "StepCompositeView",
     "kind": "class",
     "line": 537,
     "loc": 280,
     "doc": "Header, paint surface, the opacity control, and the grid controls."
    }
   ],
   "calls": [
    [
     "_CompositePane",
     "_cell_span"
    ],
    [
     "StepCompositeView",
     "_CompositePane"
    ]
   ],
   "uses": [
    [
     "_CompositePane",
     "sieve.gui.band_plot",
     "ACCENT"
    ],
    [
     "_CompositePane",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "_CompositePane",
     "sieve.gui.band_plot",
     "PANEL"
    ],
    [
     "_CompositePane",
     "sieve.gui.band_plot",
     "TEXT"
    ],
    [
     "_CompositePane",
     "sieve.gui.band_plot",
     "argb_to_qimage"
    ],
    [
     "_CompositePane",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "_CompositePane",
     "sieve.gui.zoom",
     "Magnifier"
    ],
    [
     "StepCompositeView",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "StepCompositeView",
     "sieve.gui.band_plot",
     "PANEL"
    ],
    [
     "StepCompositeView",
     "sieve.gui.band_plot",
     "plot_font"
    ]
   ]
  },
  "sieve.gui.concurrency": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 71,
   "isInit": false,
   "ghost": false,
   "doc": "The interactive session's slice: which pools it runs, and whether they fit.",
   "annotation": "",
   "external": [],
   "symbols": [
    {
     "name": "total_workers",
     "kind": "function",
     "line": 28,
     "loc": 7,
     "doc": "Threads the interactive session may run at once, across all three pools."
    },
    {
     "name": "fits_machine",
     "kind": "function",
     "line": 37,
     "loc": 10,
     "doc": "Whether the declared split leaves this machine a core for the GUI thread."
    },
    {
     "name": "resolve_worker_split",
     "kind": "function",
     "line": 49,
     "loc": 22,
     "doc": "The declared split, degraded to fit this machine's allocation."
    }
   ],
   "calls": [
    [
     "fits_machine",
     "total_workers"
    ]
   ],
   "uses": [
    [
     "total_workers",
     "sieve.mutual.shares",
     "DETECTOR_WORKERS"
    ],
    [
     "total_workers",
     "sieve.mutual.shares",
     "PLAYER_WORKERS"
    ],
    [
     "total_workers",
     "sieve.mutual.shares",
     "PREVIEW_WORKERS"
    ],
    [
     "fits_machine",
     "sieve.mutual.machine",
     "available_cpus"
    ],
    [
     "resolve_worker_split",
     "sieve.mutual.machine",
     "available_cpus"
    ],
    [
     "resolve_worker_split",
     "sieve.mutual.shares",
     "DETECTOR_WORKERS"
    ],
    [
     "resolve_worker_split",
     "sieve.mutual.shares",
     "PLAYER_WORKERS"
    ],
    [
     "resolve_worker_split",
     "sieve.mutual.shares",
     "PREVIEW_WORKERS"
    ],
    [
     "resolve_worker_split",
     "sieve.mutual.shares",
     "WorkerSplit"
    ]
   ]
  },
  "sieve.gui.count_plot": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 219,
   "isInit": false,
   "ghost": false,
   "doc": "Elements in band, windowed over D: the graph where detection becomes visible.",
   "annotation": "",
   "external": [
    "PySide6",
    "itertools",
    "math",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "CountPlot",
     "kind": "class",
     "line": 70,
     "loc": 149,
     "doc": "Windowed element count in band, gate spans, one draggable threshold."
    }
   ],
   "calls": [],
   "uses": [
    [
     "CountPlot",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "CountPlot",
     "sieve.gui.band_plot",
     "BandPlot"
    ],
    [
     "CountPlot",
     "sieve.gui.band_plot",
     "DETECT"
    ],
    [
     "CountPlot",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "CountPlot",
     "sieve.gui.band_plot",
     "plot_font"
    ]
   ]
  },
  "sieve.gui.crop_tools": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 433,
   "isInit": false,
   "ghost": false,
   "doc": "The replicate tab's right half: what a box is, and what it was cut from.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "_NumberField",
     "kind": "class",
     "line": 72,
     "loc": 73,
     "doc": "A spin box whose value, and whose claim on the keyboard, move on commit."
    },
    {
     "name": "CropToolsPanel",
     "kind": "class",
     "line": 147,
     "loc": 286,
     "doc": "Crop tools, the selected box's dimensions, and the source it came from."
    }
   ],
   "calls": [
    [
     "CropToolsPanel",
     "_NumberField"
    ]
   ],
   "uses": [
    [
     "CropToolsPanel",
     "sieve.core.types",
     "ROI"
    ],
    [
     "CropToolsPanel",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "CropToolsPanel",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "CropToolsPanel",
     "sieve.gui.video_view",
     "CropMode"
    ]
   ]
  },
  "sieve.gui.density_plot": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 252,
   "isInit": false,
   "ghost": false,
   "doc": "Band power by block: the population the count comes from, as a density.",
   "annotation": "",
   "external": [
    "PySide6",
    "dataclasses",
    "itertools",
    "math",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "bin_counts",
     "kind": "function",
     "line": 66,
     "loc": 44,
     "doc": "`(T, B)` band power binned to `(bins, T)` counts on a log1p value axis."
    },
    {
     "name": "DensitySurface",
     "kind": "class",
     "line": 113,
     "loc": 18,
     "doc": "The picture and the axis it implies, without a widget or a `QImage`."
    },
    {
     "name": "density_surface",
     "kind": "function",
     "line": 133,
     "loc": 23,
     "doc": "Bin `(T, B)` band power into the picture, off any particular thread."
    },
    {
     "name": "DensityPlot",
     "kind": "class",
     "line": 158,
     "loc": 94,
     "doc": "Per-frame value histogram over all blocks, with the value band on top."
    }
   ],
   "calls": [
    [
     "density_surface",
     "DensitySurface"
    ],
    [
     "density_surface",
     "bin_counts"
    ],
    [
     "DensityPlot",
     "DensitySurface"
    ],
    [
     "DensityPlot",
     "density_surface"
    ]
   ],
   "uses": [
    [
     "density_surface",
     "sieve.gui.band_plot",
     "ramp_lut"
    ],
    [
     "DensityPlot",
     "sieve.gui.band_plot",
     "ACCENT"
    ],
    [
     "DensityPlot",
     "sieve.gui.band_plot",
     "BandPlot"
    ],
    [
     "DensityPlot",
     "sieve.gui.band_plot",
     "argb_to_qimage"
    ]
   ]
  },
  "sieve.gui.detector_worker": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 361,
   "isInit": false,
   "ghost": false,
   "doc": "The detector's own thread: derive the graphs from a series still being filled.",
   "annotation": "",
   "external": [
    "PySide6",
    "dataclasses",
    "numpy",
    "time",
    "typing"
   ],
   "symbols": [
    {
     "name": "DetectorRequest",
     "kind": "class",
     "line": 67,
     "loc": 25,
     "doc": "One derivation to run off the GUI thread. Crosses to the worker whole."
    },
    {
     "name": "DetectorResult",
     "kind": "class",
     "line": 95,
     "loc": 31,
     "doc": "One derivation, with the frontier it is allowed to be read up to."
    },
    {
     "name": "settled_for",
     "kind": "function",
     "line": 128,
     "loc": 10,
     "doc": "The detect filter frontier with the live state converted at the boundary."
    },
    {
     "name": "derive",
     "kind": "function",
     "line": 140,
     "loc": 44,
     "doc": "The whole derivation, as a pure function. Qt-free and thread-free."
    },
    {
     "name": "DetectorFailure",
     "kind": "class",
     "line": 187,
     "loc": 9,
     "doc": "A derivation that raised, carried back so the graphs can say so."
    },
    {
     "name": "_DetectorWorker",
     "kind": "class",
     "line": 198,
     "loc": 40,
     "doc": "Lives on the detector thread. Its one slot runs off the GUI thread."
    },
    {
     "name": "DetectorRunner",
     "kind": "class",
     "line": 240,
     "loc": 121,
     "doc": "Derives the detector off the GUI thread, one pass in flight at a time."
    }
   ],
   "calls": [
    [
     "derive",
     "DetectorRequest"
    ],
    [
     "derive",
     "DetectorResult"
    ],
    [
     "_DetectorWorker",
     "DetectorFailure"
    ],
    [
     "_DetectorWorker",
     "DetectorRequest"
    ],
    [
     "_DetectorWorker",
     "derive"
    ],
    [
     "DetectorRunner",
     "DetectorFailure"
    ],
    [
     "DetectorRunner",
     "DetectorRequest"
    ],
    [
     "DetectorRunner",
     "DetectorResult"
    ],
    [
     "DetectorRunner",
     "_DetectorWorker"
    ]
   ],
   "uses": [
    [
     "DetectorRequest",
     "sieve.gui.chain_model",
     "DetectorState"
    ],
    [
     "DetectorResult",
     "sieve.filters.detect",
     "DetectorUpdate"
    ],
    [
     "DetectorResult",
     "sieve.gui.density_plot",
     "DensitySurface"
    ],
    [
     "settled_for",
     "sieve.filters.detect",
     "DetectParams"
    ],
    [
     "settled_for",
     "sieve.filters.detect",
     "detect"
    ],
    [
     "settled_for",
     "sieve.gui.chain_model",
     "DetectorState"
    ],
    [
     "derive",
     "sieve.filters.detect",
     "DetectParams"
    ],
    [
     "derive",
     "sieve.filters.detect",
     "detect"
    ],
    [
     "derive",
     "sieve.gui.concurrency",
     "resolve_worker_split"
    ],
    [
     "derive",
     "sieve.gui.density_plot",
     "density_surface"
    ],
    [
     "_DetectorWorker",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "DetectorRunner",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ]
   ]
  },
  "sieve.gui.document": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 1252,
   "isInit": false,
   "ghost": false,
   "doc": "The editable replicate document: a `ReplicateSet` plus its undo history.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections",
    "dataclasses",
    "fractions",
    "pathlib",
    "typing"
   ],
   "symbols": [
    {
     "name": "DocumentState",
     "kind": "class",
     "line": 70,
     "loc": 23,
     "doc": "The whole of what a document owns, in one comparable value."
    },
    {
     "name": "_Gesture",
     "kind": "class",
     "line": 96,
     "loc": 6,
     "doc": "One continuous geometry drag, and the box it started from."
    },
    {
     "name": "ReplicateDocument",
     "kind": "class",
     "line": 104,
     "loc": 1148,
     "doc": "Ordered replicates for one source video, with undo/redo."
    }
   ],
   "calls": [
    [
     "ReplicateDocument",
     "DocumentState"
    ],
    [
     "ReplicateDocument",
     "_Gesture"
    ]
   ],
   "uses": [
    [
     "DocumentState",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "DocumentState",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "DocumentState",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "DocumentState",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_Gesture",
     "sieve.core.types",
     "ROI"
    ],
    [
     "ReplicateDocument",
     "sieve.core.clip_window",
     "DEFAULT_WINDOW_SECONDS"
    ],
    [
     "ReplicateDocument",
     "sieve.core.clip_window",
     "containing"
    ],
    [
     "ReplicateDocument",
     "sieve.core.clip_window",
     "effective_window"
    ],
    [
     "ReplicateDocument",
     "sieve.core.clip_window",
     "ended_at"
    ],
    [
     "ReplicateDocument",
     "sieve.core.clip_window",
     "fitted"
    ],
    [
     "ReplicateDocument",
     "sieve.core.clip_window",
     "moved_to"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "DetectorSettings"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "edited_detector"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "edited_params"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "equivalence_groups"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "resolved_detector"
    ],
    [
     "ReplicateDocument",
     "sieve.core.pipeline_model",
     "resolved_params"
    ],
    [
     "ReplicateDocument",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "ReplicateDocument",
     "sieve.core.replicates",
     "ReplicateSet"
    ],
    [
     "ReplicateDocument",
     "sieve.core.types",
     "ROI"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "AddReplicate"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "EditDetector"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "EditTuningParams"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "RemoveReplicate"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "RenameReplicate"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "ResetTuning"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "RestoreSnapshot"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "SetClip"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "SetReplicateROI"
    ],
    [
     "ReplicateDocument",
     "sieve.gui.commands",
     "SetReplicateROIs"
    ],
    [
     "ReplicateDocument",
     "sieve.pipeline.crop_binding",
     "CropBacking"
    ],
    [
     "ReplicateDocument",
     "sieve.pipeline.crop_binding",
     "CropState"
    ],
    [
     "ReplicateDocument",
     "sieve.pipeline.crop_binding",
     "backing_for"
    ],
    [
     "ReplicateDocument",
     "sieve.pipeline.dag",
     "graph_needs_chroma"
    ],
    [
     "ReplicateDocument",
     "sieve.pipeline.source_home",
     "SourceHome"
    ]
   ]
  },
  "sieve.gui.editing_sources": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 52,
   "isInit": false,
   "ghost": false,
   "doc": "Who is being edited right now \u2014 a set of sources, not a flag.",
   "annotation": "",
   "external": [],
   "symbols": [
    {
     "name": "EditingSources",
     "kind": "class",
     "line": 32,
     "loc": 20,
     "doc": ""
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.executor_adapter": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 111,
   "isInit": false,
   "ghost": false,
   "doc": "The one place that knows both the metric bus and Qt.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "ExecutorAdapter",
     "kind": "class",
     "line": 43,
     "loc": 68,
     "doc": "Subscribes to a `MetricBus`, emits its samples on the GUI thread."
    }
   ],
   "calls": [],
   "uses": [
    [
     "ExecutorAdapter",
     "sieve.bench.metrics",
     "METRICS"
    ],
    [
     "ExecutorAdapter",
     "sieve.bench.metrics",
     "MetricBus"
    ],
    [
     "ExecutorAdapter",
     "sieve.bench.metrics",
     "Sample"
    ]
   ]
  },
  "sieve.gui.filter_tab": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 2322,
   "isInit": false,
   "ghost": false,
   "doc": "The filter tab: the live chain on the right, where the signal is on the left.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections",
    "dataclasses",
    "itertools",
    "json",
    "math",
    "numpy",
    "time",
    "typing"
   ],
   "symbols": [
    {
     "name": "_RescaleCostRun",
     "kind": "class",
     "line": 159,
     "loc": 7,
     "doc": "A window render whose wall clock should become one cost sample."
    },
    {
     "name": "_block_signal_label",
     "kind": "function",
     "line": 168,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "FilterTab",
     "kind": "class",
     "line": 181,
     "loc": 2126,
     "doc": "The live preprocessing chain and its detector, for one source video."
    },
    {
     "name": "_row",
     "kind": "function",
     "line": 2309,
     "loc": 13,
     "doc": "One caption-labelled parameter row, persistent across stack rebuilds."
    }
   ],
   "calls": [
    [
     "FilterTab",
     "_RescaleCostRun"
    ],
    [
     "FilterTab",
     "_block_signal_label"
    ],
    [
     "FilterTab",
     "_row"
    ]
   ],
   "uses": [
    [
     "_block_signal_label",
     "sieve.filters.block_signal",
     "BlockSignalParams"
    ],
    [
     "FilterTab",
     "sieve.bench.metrics",
     "METRICS"
    ],
    [
     "FilterTab",
     "sieve.bench.metrics",
     "MetricBus"
    ],
    [
     "FilterTab",
     "sieve.core.ops.wavelet",
     "default_freqs"
    ],
    [
     "FilterTab",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "FilterTab",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "FilterTab",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "FilterTab",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "FilterTab",
     "sieve.core.types",
     "WallTime"
    ],
    [
     "FilterTab",
     "sieve.filters.block_signal",
     "Signal"
    ],
    [
     "FilterTab",
     "sieve.filters.block_signal",
     "resolve_block"
    ],
    [
     "FilterTab",
     "sieve.filters.detect",
     "gate_to"
    ],
    [
     "FilterTab",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "FilterTab",
     "sieve.gui.block_spin",
     "BlockSpinBox"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "BLOCK_SIGNAL_ELEMENT_NAMES"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "ChainKind"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "DetectorState"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "DetectorUpdate"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "Status"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "caption_for"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "parity_chain"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "recompute"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_model",
     "snapped_band_label"
    ],
    [
     "FilterTab",
     "sieve.gui.chain_stack",
     "ChainStackView"
    ],
    [
     "FilterTab",
     "sieve.gui.commit_combo",
     "CommitCombo"
    ],
    [
     "FilterTab",
     "sieve.gui.composite_view",
     "StepCompositeView"
    ],
    [
     "FilterTab",
     "sieve.gui.concurrency",
     "resolve_worker_split"
    ],
    [
     "FilterTab",
     "sieve.gui.count_plot",
     "CountPlot"
    ],
    [
     "FilterTab",
     "sieve.gui.density_plot",
     "DensityPlot"
    ],
    [
     "FilterTab",
     "sieve.gui.density_plot",
     "DensitySurface"
    ],
    [
     "FilterTab",
     "sieve.gui.detector_worker",
     "DetectorFailure"
    ],
    [
     "FilterTab",
     "sieve.gui.detector_worker",
     "DetectorRequest"
    ],
    [
     "FilterTab",
     "sieve.gui.detector_worker",
     "DetectorResult"
    ],
    [
     "FilterTab",
     "sieve.gui.detector_worker",
     "DetectorRunner"
    ],
    [
     "FilterTab",
     "sieve.gui.detector_worker",
     "settled_for"
    ],
    [
     "FilterTab",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "FilterTab",
     "sieve.gui.graph_hud",
     "GraphHud"
    ],
    [
     "FilterTab",
     "sieve.gui.gray_toggle",
     "GrayToggle"
    ],
    [
     "FilterTab",
     "sieve.gui.materialize_worker",
     "MaterializeRunner"
    ],
    [
     "FilterTab",
     "sieve.gui.param_form",
     "param_rows"
    ],
    [
     "FilterTab",
     "sieve.gui.preferences",
     "Preferences"
    ],
    [
     "FilterTab",
     "sieve.gui.preview_runner",
     "PreviewRunner"
    ],
    [
     "FilterTab",
     "sieve.gui.rescale_cost",
     "RescaleCostHistory"
    ],
    [
     "FilterTab",
     "sieve.gui.rescale_cost",
     "RescaleCostSample"
    ],
    [
     "FilterTab",
     "sieve.gui.rescale_cost",
     "format_rescale_cost"
    ],
    [
     "FilterTab",
     "sieve.gui.scalogram_plot",
     "ScalogramPlot"
    ],
    [
     "FilterTab",
     "sieve.gui.source_boundary",
     "SourceBoundary"
    ],
    [
     "FilterTab",
     "sieve.gui.transport.player",
     "VideoPlayer"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard",
     "StepWizard"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard",
     "frame_to_qimage"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard_lifecycle",
     "WizardAccepted"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard_lifecycle",
     "WizardCancelled"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard_lifecycle",
     "WizardLifecycle"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard_model",
     "catalog"
    ],
    [
     "FilterTab",
     "sieve.gui.wizard_model",
     "chain_from_pipeline"
    ],
    [
     "FilterTab",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "FilterTab",
     "sieve.pipeline.preview",
     "PreviewRender"
    ],
    [
     "FilterTab",
     "sieve.pipeline.series_collector",
     "SeriesCollector"
    ],
    [
     "_row",
     "sieve.gui.band_plot",
     "DIM"
    ]
   ]
  },
  "sieve.gui.graph_hud": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 297,
   "isInit": false,
   "ghost": false,
   "doc": "The graph HUD: what each frame of the working window cost, as a plot.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "GraphHud",
     "kind": "class",
     "line": 103,
     "loc": 194,
     "doc": "Per-frame render cost over the working window, playhead as cursor."
    }
   ],
   "calls": [],
   "uses": [
    [
     "GraphHud",
     "sieve.bench.metrics",
     "Sample"
    ],
    [
     "GraphHud",
     "sieve.gui.band_plot",
     "ACCENT"
    ],
    [
     "GraphHud",
     "sieve.gui.band_plot",
     "BAND"
    ],
    [
     "GraphHud",
     "sieve.gui.band_plot",
     "BandPlot"
    ],
    [
     "GraphHud",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "GraphHud",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "GraphHud",
     "sieve.gui.resource_probe",
     "ResourceSample"
    ]
   ]
  },
  "sieve.gui.gray_toggle": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 142,
   "isInit": false,
   "ghost": false,
   "doc": "The viewport's gray toggle: the affordance lives where the symptom is.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "GrayToggle",
     "kind": "class",
     "line": 65,
     "loc": 77,
     "doc": "The one control over the viewport's decode format."
    }
   ],
   "calls": [],
   "uses": [
    [
     "GrayToggle",
     "sieve.gui.preferences",
     "Preferences"
    ]
   ]
  },
  "sieve.gui.history_dialog": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 116,
   "isInit": false,
   "ghost": false,
   "doc": "File \u25b8 History: pick a point to roll back to.",
   "annotation": "",
   "external": [
    "PySide6",
    "time"
   ],
   "symbols": [
    {
     "name": "age_text",
     "kind": "function",
     "line": 36,
     "loc": 17,
     "doc": "How long ago, in the coarsest unit that still distinguishes two entries."
    },
    {
     "name": "HistoryDialog",
     "kind": "class",
     "line": 66,
     "loc": 50,
     "doc": ""
    }
   ],
   "calls": [
    [
     "HistoryDialog",
     "age_text"
    ]
   ],
   "uses": [
    [
     "HistoryDialog",
     "sieve.core.history",
     "Snapshot"
    ]
   ]
  },
  "sieve.gui.keyboard_handback": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 58,
   "isInit": false,
   "ghost": false,
   "doc": "Enter and Esc hand the keyboard back, so the spacebar plays again.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "KeyboardHandback",
     "kind": "class",
     "line": 46,
     "loc": 12,
     "doc": ""
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.main_window": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 1103,
   "isInit": false,
   "ghost": false,
   "doc": "Top-level window: menus, tabs, the timeline, and the wiring between them.",
   "annotation": "",
   "external": [
    "PySide6",
    "pathlib",
    "pydantic",
    "yaml"
   ],
   "symbols": [
    {
     "name": "MainWindow",
     "kind": "class",
     "line": 100,
     "loc": 1003,
     "doc": "The SIEVE desktop window."
    }
   ],
   "calls": [],
   "uses": [
    [
     "MainWindow",
     "sieve.core.history",
     "SnapshotStore"
    ],
    [
     "MainWindow",
     "sieve.core.history",
     "history_directory"
    ],
    [
     "MainWindow",
     "sieve.core.pipeline_model",
     "Project"
    ],
    [
     "MainWindow",
     "sieve.core.pipeline_model",
     "as_project_path"
    ],
    [
     "MainWindow",
     "sieve.core.pipeline_model",
     "project_path_for"
    ],
    [
     "MainWindow",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "MainWindow",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "MainWindow",
     "sieve.gui.executor_adapter",
     "ExecutorAdapter"
    ],
    [
     "MainWindow",
     "sieve.gui.filter_tab",
     "FilterTab"
    ],
    [
     "MainWindow",
     "sieve.gui.history_dialog",
     "HistoryDialog"
    ],
    [
     "MainWindow",
     "sieve.gui.preferences",
     "Preferences"
    ],
    [
     "MainWindow",
     "sieve.gui.preferences_dialog",
     "PreferencesDialog"
    ],
    [
     "MainWindow",
     "sieve.gui.preview_runner",
     "PreviewRunner"
    ],
    [
     "MainWindow",
     "sieve.gui.replicate_tab",
     "ReplicateTab"
    ],
    [
     "MainWindow",
     "sieve.gui.resource_probe",
     "MODE_IDLE"
    ],
    [
     "MainWindow",
     "sieve.gui.resource_probe",
     "MODE_PLAYBACK"
    ],
    [
     "MainWindow",
     "sieve.gui.resource_probe",
     "MODE_RENDER"
    ],
    [
     "MainWindow",
     "sieve.gui.resource_probe",
     "MODE_RENDER_FED_PLAYBACK"
    ],
    [
     "MainWindow",
     "sieve.gui.resource_probe",
     "ResourceProbe"
    ],
    [
     "MainWindow",
     "sieve.gui.timeline.bar",
     "TimelineBar"
    ],
    [
     "MainWindow",
     "sieve.gui.toast",
     "Toast"
    ],
    [
     "MainWindow",
     "sieve.gui.transport.player",
     "VideoPlayer"
    ],
    [
     "MainWindow",
     "sieve.pipeline.preview",
     "PreviewRender"
    ],
    [
     "MainWindow",
     "sieve.pipeline.source_home",
     "SourceHome"
    ]
   ]
  },
  "sieve.gui.materialize_worker": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 192,
   "isInit": false,
   "ghost": false,
   "doc": "The write pass on its own thread: one crop, cut while the GUI stays alive.",
   "annotation": "",
   "external": [
    "PySide6",
    "dataclasses",
    "pathlib"
   ],
   "symbols": [
    {
     "name": "MaterializeRequest",
     "kind": "class",
     "line": 37,
     "loc": 17,
     "doc": "One cut to write. Crosses to the worker whole."
    },
    {
     "name": "_Worker",
     "kind": "class",
     "line": 56,
     "loc": 50,
     "doc": "Lives on the write thread. Its one slot runs off the GUI thread."
    },
    {
     "name": "MaterializeRunner",
     "kind": "class",
     "line": 108,
     "loc": 84,
     "doc": "Writes crop artifacts off the GUI thread, one at a time."
    }
   ],
   "calls": [
    [
     "_Worker",
     "MaterializeRequest"
    ],
    [
     "MaterializeRunner",
     "MaterializeRequest"
    ],
    [
     "MaterializeRunner",
     "_Worker"
    ]
   ],
   "uses": [
    [
     "MaterializeRequest",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "MaterializeRequest",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_Worker",
     "sieve.pipeline.materialize",
     "MaterializeCancelledError"
    ],
    [
     "_Worker",
     "sieve.pipeline.materialize",
     "materialize_crop"
    ],
    [
     "MaterializeRunner",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ]
   ]
  },
  "sieve.gui.param_form": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 146,
   "isInit": false,
   "ghost": false,
   "doc": "Parameter rows for a node, built from its registered params model.",
   "annotation": "",
   "external": [
    "PySide6",
    "annotated_types",
    "collections",
    "enum",
    "typing"
   ],
   "symbols": [
    {
     "name": "param_rows",
     "kind": "function",
     "line": 44,
     "loc": 15,
     "doc": ""
    },
    {
     "name": "_widget_for",
     "kind": "function",
     "line": 61,
     "loc": 57,
     "doc": ""
    },
    {
     "name": "_bounds",
     "kind": "function",
     "line": 120,
     "loc": 13,
     "doc": ""
    },
    {
     "name": "_row",
     "kind": "function",
     "line": 135,
     "loc": 11,
     "doc": ""
    }
   ],
   "calls": [
    [
     "param_rows",
     "_row"
    ],
    [
     "param_rows",
     "_widget_for"
    ],
    [
     "_widget_for",
     "_bounds"
    ]
   ],
   "uses": [
    [
     "param_rows",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "param_rows",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "_widget_for",
     "sieve.gui.commit_combo",
     "CommitCombo"
    ],
    [
     "_row",
     "sieve.gui.band_plot",
     "DIM"
    ]
   ]
  },
  "sieve.gui.preferences": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 300,
   "isInit": false,
   "ghost": false,
   "doc": "User preferences: typed accessors over `QSettings`, with change signals.",
   "annotation": "",
   "external": [
    "PySide6",
    "pathlib",
    "typing"
   ],
   "symbols": [
    {
     "name": "Preferences",
     "kind": "class",
     "line": 84,
     "loc": 180,
     "doc": "The application's preferences, persisted immediately on change."
    },
    {
     "name": "_clamp",
     "kind": "function",
     "line": 266,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "_as_bool",
     "kind": "function",
     "line": 270,
     "loc": 11,
     "doc": "Coerce a stored value to bool. INI files hand back `\"true\"`, not `True`."
    },
    {
     "name": "_as_float",
     "kind": "function",
     "line": 283,
     "loc": 17,
     "doc": "Coerce a stored value to a float inside `[low, high]`, or the default."
    }
   ],
   "calls": [
    [
     "Preferences",
     "_as_bool"
    ],
    [
     "Preferences",
     "_as_float"
    ],
    [
     "Preferences",
     "_clamp"
    ],
    [
     "_as_float",
     "_clamp"
    ]
   ],
   "uses": [
    [
     "Preferences",
     "sieve.core.clip_window",
     "DEFAULT_WINDOW_SECONDS"
    ]
   ]
  },
  "sieve.gui.preferences_dialog": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 216,
   "isInit": false,
   "ghost": false,
   "doc": "The Preferences pane.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "PreferencesDialog",
     "kind": "class",
     "line": 70,
     "loc": 138,
     "doc": ""
    },
    {
     "name": "_help_label",
     "kind": "function",
     "line": 210,
     "loc": 6,
     "doc": ""
    }
   ],
   "calls": [
    [
     "PreferencesDialog",
     "_help_label"
    ]
   ],
   "uses": [
    [
     "PreferencesDialog",
     "sieve.gui.preferences",
     "MAX_COARSE_INTERVAL_SECONDS"
    ],
    [
     "PreferencesDialog",
     "sieve.gui.preferences",
     "MAX_PROXY_WIDTH"
    ],
    [
     "PreferencesDialog",
     "sieve.gui.preferences",
     "MIN_COARSE_INTERVAL_SECONDS"
    ],
    [
     "PreferencesDialog",
     "sieve.gui.preferences",
     "MIN_PROXY_WIDTH"
    ],
    [
     "PreferencesDialog",
     "sieve.gui.preferences",
     "Preferences"
    ]
   ]
  },
  "sieve.gui.preview_runner": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 1067,
   "isInit": false,
   "ghost": false,
   "doc": "The GUI's producer of graph timings: a `PreviewSession` on a thread of its own.",
   "annotation": "",
   "external": [
    "PySide6",
    "dataclasses",
    "pathlib",
    "pydantic",
    "threading",
    "time"
   ],
   "symbols": [
    {
     "name": "_AbandonedError",
     "kind": "class",
     "line": 110,
     "loc": 7,
     "doc": "Raised out of the frame consumer to drop a render that is no longer wanted."
    },
    {
     "name": "_Wanted",
     "kind": "class",
     "line": 119,
     "loc": 22,
     "doc": "The newest revision, read by the render thread and written by the GUI's."
    },
    {
     "name": "RenderRequest",
     "kind": "class",
     "line": 144,
     "loc": 38,
     "doc": "One submitted render. Crosses to the worker thread whole."
    },
    {
     "name": "_Crops",
     "kind": "class",
     "line": 185,
     "loc": 13,
     "doc": "The project's crop artifacts, as the render thread sees them."
    },
    {
     "name": "_RenderWorker",
     "kind": "class",
     "line": 200,
     "loc": 371,
     "doc": "Lives on the render thread. Every slot here runs off the GUI thread."
    },
    {
     "name": "PreviewRunner",
     "kind": "class",
     "line": 573,
     "loc": 494,
     "doc": "Renders the working window off the event loop and reports what each frame cost."
    }
   ],
   "calls": [
    [
     "_RenderWorker",
     "RenderRequest"
    ],
    [
     "_RenderWorker",
     "_AbandonedError"
    ],
    [
     "_RenderWorker",
     "_Crops"
    ],
    [
     "_RenderWorker",
     "_Wanted"
    ],
    [
     "PreviewRunner",
     "RenderRequest"
    ],
    [
     "PreviewRunner",
     "_Crops"
    ],
    [
     "PreviewRunner",
     "_RenderWorker"
    ],
    [
     "PreviewRunner",
     "_Wanted"
    ]
   ],
   "uses": [
    [
     "RenderRequest",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "RenderRequest",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "RenderRequest",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "RenderRequest",
     "sieve.pipeline.preview",
     "Consumer"
    ],
    [
     "_Crops",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "_RenderWorker",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "_RenderWorker",
     "sieve.backend.dispatch",
     "KernelRegistry"
    ],
    [
     "_RenderWorker",
     "sieve.backend.dispatch",
     "NoKernelError"
    ],
    [
     "_RenderWorker",
     "sieve.bench.metrics",
     "MetricBus"
    ],
    [
     "_RenderWorker",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "_RenderWorker",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "_RenderWorker",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "_RenderWorker",
     "sieve.decode.ffmpeg",
     "FfmpegLoweredFrameSource"
    ],
    [
     "_RenderWorker",
     "sieve.decode.ffmpeg",
     "ffmpeg_decoder_identity"
    ],
    [
     "_RenderWorker",
     "sieve.decode.prefetch",
     "PrefetchFrameSource"
    ],
    [
     "_RenderWorker",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "_RenderWorker",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "_RenderWorker",
     "sieve.gui.concurrency",
     "resolve_worker_split"
    ],
    [
     "_RenderWorker",
     "sieve.gui.transport.render_ring",
     "RenderFrameRing"
    ],
    [
     "_RenderWorker",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.dag",
     "GraphError"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.executor",
     "FrameResult"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.executor",
     "UnrunnableNodeError"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.lowering",
     "lower_resolved_source"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.preview",
     "PreviewSession"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.resolve_source",
     "resolve"
    ],
    [
     "_RenderWorker",
     "sieve.pipeline.source_home",
     "SourceHome"
    ],
    [
     "PreviewRunner",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "PreviewRunner",
     "sieve.backend.dispatch",
     "KernelRegistry"
    ],
    [
     "PreviewRunner",
     "sieve.bench.metrics",
     "METRICS"
    ],
    [
     "PreviewRunner",
     "sieve.bench.metrics",
     "MetricBus"
    ],
    [
     "PreviewRunner",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "PreviewRunner",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "PreviewRunner",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "PreviewRunner",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "PreviewRunner",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "PreviewRunner",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "PreviewRunner",
     "sieve.gui.transport.render_ring",
     "RenderFrameRing"
    ],
    [
     "PreviewRunner",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "PreviewRunner",
     "sieve.pipeline.cache_key",
     "source_identity"
    ],
    [
     "PreviewRunner",
     "sieve.pipeline.dag",
     "graph_needs_chroma"
    ],
    [
     "PreviewRunner",
     "sieve.pipeline.preview",
     "Consumer"
    ],
    [
     "PreviewRunner",
     "sieve.pipeline.preview",
     "PreviewRender"
    ]
   ]
  },
  "sieve.gui.replicate_tab": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 390,
   "isInit": false,
   "ghost": false,
   "doc": "The Replicate tab: viewport on top, replicate table below, split evenly.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "ReplicateTab",
     "kind": "class",
     "line": 55,
     "loc": 335,
     "doc": "Viewport and replicate table for one source video."
    }
   ],
   "calls": [],
   "uses": [
    [
     "ReplicateTab",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "ReplicateTab",
     "sieve.core.types",
     "ROI"
    ],
    [
     "ReplicateTab",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "ReplicateTab",
     "sieve.gui.crop_tools",
     "CropToolsPanel"
    ],
    [
     "ReplicateTab",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "ReplicateTab",
     "sieve.gui.editing_sources",
     "EditingSources"
    ],
    [
     "ReplicateTab",
     "sieve.gui.replicate_table",
     "Column"
    ],
    [
     "ReplicateTab",
     "sieve.gui.replicate_table",
     "EditingAwareDelegate"
    ],
    [
     "ReplicateTab",
     "sieve.gui.replicate_table",
     "ReplicateTableModel"
    ],
    [
     "ReplicateTab",
     "sieve.gui.transport.player",
     "VideoPlayer"
    ],
    [
     "ReplicateTab",
     "sieve.gui.video_view",
     "CropMode"
    ],
    [
     "ReplicateTab",
     "sieve.gui.video_view",
     "NO_SELECTION"
    ],
    [
     "ReplicateTab",
     "sieve.gui.video_view",
     "VideoView"
    ]
   ]
  },
  "sieve.gui.replicate_table": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 260,
   "isInit": false,
   "ghost": false,
   "doc": "Table view over the replicate document.",
   "annotation": "",
   "external": [
    "PySide6",
    "enum",
    "typing"
   ],
   "symbols": [
    {
     "name": "Column",
     "kind": "class",
     "line": 27,
     "loc": 10,
     "doc": "Table columns, in display order."
    },
    {
     "name": "ReplicateTableModel",
     "kind": "class",
     "line": 63,
     "loc": 135,
     "doc": "Rows are replicates; geometry is editable in source pixels."
    },
    {
     "name": "EditingAwareDelegate",
     "kind": "class",
     "line": 200,
     "loc": 60,
     "doc": "Reports which cell editors are open, by name."
    }
   ],
   "calls": [
    [
     "ReplicateTableModel",
     "Column"
    ]
   ],
   "uses": [
    [
     "ReplicateTableModel",
     "sieve.core.types",
     "ROI"
    ],
    [
     "ReplicateTableModel",
     "sieve.gui.document",
     "ReplicateDocument"
    ]
   ]
  },
  "sieve.gui.rescale_cost": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 292,
   "isInit": false,
   "ghost": false,
   "doc": "Measured wall-clock model for the live rescale knob.",
   "annotation": "",
   "external": [
    "dataclasses",
    "math"
   ],
   "symbols": [
    {
     "name": "Provisional",
     "kind": "class",
     "line": 56,
     "loc": 7,
     "doc": "Why no curve is being reported, in the words the readout will use."
    },
    {
     "name": "RescaleCostSample",
     "kind": "class",
     "line": 102,
     "loc": 28,
     "doc": "One completed window render in the context it measured."
    },
    {
     "name": "RescaleCostFit",
     "kind": "class",
     "line": 133,
     "loc": 37,
     "doc": "A fit of `F + M*s**2` for one measured context."
    },
    {
     "name": "fit_rescale_cost",
     "kind": "function",
     "line": 172,
     "loc": 36,
     "doc": "Fit the current context's samples, or report why no fit can be shown."
    },
    {
     "name": "_refused",
     "kind": "function",
     "line": 210,
     "loc": 7,
     "doc": ""
    },
    {
     "name": "_fit_quality",
     "kind": "function",
     "line": 219,
     "loc": 13,
     "doc": "Share of the spread in `ys` the fitted line accounts for."
    },
    {
     "name": "_sample_list",
     "kind": "function",
     "line": 234,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "RescaleCostHistory",
     "kind": "class",
     "line": 239,
     "loc": 36,
     "doc": "Measured samples for one context; a context change clears the fit."
    },
    {
     "name": "format_rescale_cost",
     "kind": "function",
     "line": 277,
     "loc": 15,
     "doc": "Compact label text for the rescale row."
    }
   ],
   "calls": [
    [
     "RescaleCostFit",
     "Provisional"
    ],
    [
     "fit_rescale_cost",
     "RescaleCostFit"
    ],
    [
     "fit_rescale_cost",
     "RescaleCostSample"
    ],
    [
     "fit_rescale_cost",
     "_fit_quality"
    ],
    [
     "fit_rescale_cost",
     "_refused"
    ],
    [
     "_refused",
     "Provisional"
    ],
    [
     "_refused",
     "RescaleCostFit"
    ],
    [
     "_sample_list",
     "RescaleCostSample"
    ],
    [
     "RescaleCostHistory",
     "RescaleCostFit"
    ],
    [
     "RescaleCostHistory",
     "RescaleCostSample"
    ],
    [
     "RescaleCostHistory",
     "_sample_list"
    ],
    [
     "RescaleCostHistory",
     "fit_rescale_cost"
    ],
    [
     "format_rescale_cost",
     "RescaleCostFit"
    ]
   ],
   "uses": [
    [
     "RescaleCostSample",
     "sieve.core.types",
     "WallTime"
    ],
    [
     "RescaleCostFit",
     "sieve.core.types",
     "WallTime"
    ],
    [
     "fit_rescale_cost",
     "sieve.core.types",
     "WallTime"
    ],
    [
     "_refused",
     "sieve.core.types",
     "WallTime"
    ]
   ]
  },
  "sieve.gui.resource_probe": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 236,
   "isInit": false,
   "ghost": false,
   "doc": "The resource side of the HUD wiring: what the session holds and what the pools do.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections",
    "dataclasses",
    "time"
   ],
   "symbols": [
    {
     "name": "PoolReading",
     "kind": "class",
     "line": 68,
     "loc": 11,
     "doc": "One pool's interval, as resolved for this machine."
    },
    {
     "name": "ResourceSample",
     "kind": "class",
     "line": 82,
     "loc": 23,
     "doc": "One tick's readings, already judged against the ledger."
    },
    {
     "name": "_MemoryWorker",
     "kind": "class",
     "line": 107,
     "loc": 19,
     "doc": "Lives on the sampler thread; the only place the expensive read runs."
    },
    {
     "name": "ResourceProbe",
     "kind": "class",
     "line": 128,
     "loc": 108,
     "doc": "Samples the session's resources once a second and publishes on the GUI thread."
    }
   ],
   "calls": [
    [
     "ResourceSample",
     "PoolReading"
    ],
    [
     "_MemoryWorker",
     "PoolReading"
    ],
    [
     "_MemoryWorker",
     "ResourceSample"
    ],
    [
     "ResourceProbe",
     "PoolReading"
    ],
    [
     "ResourceProbe",
     "_MemoryWorker"
    ]
   ],
   "uses": [
    [
     "_MemoryWorker",
     "sieve.mutual.machine",
     "MemoryUnreadableError"
    ],
    [
     "_MemoryWorker",
     "sieve.mutual.shares",
     "ledger_ceiling"
    ],
    [
     "ResourceProbe",
     "sieve.gui.concurrency",
     "resolve_worker_split"
    ],
    [
     "ResourceProbe",
     "sieve.mutual.machine",
     "process_memory_bytes"
    ],
    [
     "ResourceProbe",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "ResourceProbe",
     "sieve.mutual.shares",
     "WorkerSplit"
    ]
   ]
  },
  "sieve.gui.scalogram_plot": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 157,
   "isInit": false,
   "ghost": false,
   "doc": "The scalogram: pooled Morlet power on a log-frequency axis, band on top.",
   "annotation": "",
   "external": [
    "PySide6",
    "math",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "ScalogramPlot",
     "kind": "class",
     "line": 56,
     "loc": 101,
     "doc": "Pooled Morlet power over the working window, frequency band handles."
    }
   ],
   "calls": [],
   "uses": [
    [
     "ScalogramPlot",
     "sieve.core.ops.wavelet",
     "coi_edge_samples"
    ],
    [
     "ScalogramPlot",
     "sieve.gui.band_plot",
     "BandPlot"
    ],
    [
     "ScalogramPlot",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "ScalogramPlot",
     "sieve.gui.band_plot",
     "argb_to_qimage"
    ],
    [
     "ScalogramPlot",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "ScalogramPlot",
     "sieve.gui.band_plot",
     "ramp_lut"
    ]
   ]
  },
  "sieve.gui.source_boundary": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 307,
   "isInit": false,
   "ghost": false,
   "doc": "The source boundary: the card above the stack, and the write pass behind it.",
   "annotation": "",
   "external": [
    "PySide6",
    "datetime"
   ],
   "symbols": [
    {
     "name": "SourceBoundary",
     "kind": "class",
     "line": 30,
     "loc": 277,
     "doc": "What the chain consumes, and the gesture that puts it at rest."
    }
   ],
   "calls": [],
   "uses": [
    [
     "SourceBoundary",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "SourceBoundary",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "SourceBoundary",
     "sieve.gui.chain_stack",
     "MATERIALIZE_PRICE"
    ],
    [
     "SourceBoundary",
     "sieve.gui.chain_stack",
     "SourceCard"
    ],
    [
     "SourceBoundary",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "SourceBoundary",
     "sieve.gui.materialize_worker",
     "MaterializeRequest"
    ],
    [
     "SourceBoundary",
     "sieve.gui.materialize_worker",
     "MaterializeRunner"
    ],
    [
     "SourceBoundary",
     "sieve.pipeline.crop_binding",
     "CropBacking"
    ],
    [
     "SourceBoundary",
     "sieve.pipeline.crop_binding",
     "CropState"
    ],
    [
     "SourceBoundary",
     "sieve.pipeline.crop_binding",
     "evidence_for"
    ]
   ]
  },
  "sieve.gui.timeline.__init__": {
   "package": "sieve.gui.timeline",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 13,
   "isInit": true,
   "ghost": false,
   "doc": "The full-width band: where a frame lands on the strip, and what a click means.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.gui.timeline.bar": {
   "package": "sieve.gui.timeline",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 715,
   "isInit": false,
   "ghost": false,
   "doc": "The anchor: one full-width band across the bottom of the window.",
   "annotation": "",
   "external": [
    "PySide6",
    "enum"
   ],
   "symbols": [
    {
     "name": "Grab",
     "kind": "class",
     "line": 108,
     "loc": 16,
     "doc": "What a press on the band is taking hold of."
    },
    {
     "name": "format_timecode",
     "kind": "function",
     "line": 126,
     "loc": 10,
     "doc": "`M:SS.mmm`, or `H:MM:SS.mmm` past an hour."
    },
    {
     "name": "TimelineStrip",
     "kind": "class",
     "line": 138,
     "loc": 338,
     "doc": "The band itself: the whole asset, the window on it, and the playhead."
    },
    {
     "name": "TimelineBar",
     "kind": "class",
     "line": 478,
     "loc": 237,
     "doc": "The strip and the row of controls above it."
    }
   ],
   "calls": [
    [
     "TimelineStrip",
     "Grab"
    ],
    [
     "TimelineStrip",
     "format_timecode"
    ],
    [
     "TimelineBar",
     "TimelineStrip"
    ],
    [
     "TimelineBar",
     "format_timecode"
    ]
   ],
   "uses": [
    [
     "TimelineStrip",
     "sieve.core.clip_window",
     "ended_at_handle"
    ],
    [
     "TimelineStrip",
     "sieve.core.clip_window",
     "moved_to"
    ],
    [
     "TimelineStrip",
     "sieve.core.clip_window",
     "started_at"
    ],
    [
     "TimelineStrip",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "TimelineStrip",
     "sieve.gui.timeline.geometry",
     "Geometry"
    ],
    [
     "TimelineBar",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "TimelineBar",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "TimelineBar",
     "sieve.gui.document",
     "ReplicateDocument"
    ],
    [
     "TimelineBar",
     "sieve.gui.transport.player",
     "VideoPlayer"
    ]
   ]
  },
  "sieve.gui.timeline.geometry": {
   "package": "sieve.gui.timeline",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 91,
   "isInit": false,
   "ghost": false,
   "doc": "Where a frame lands on the strip, and which frame a pixel names.",
   "annotation": "",
   "external": [
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "Geometry",
     "kind": "class",
     "line": 28,
     "loc": 63,
     "doc": "The frame\u2194column mapping for a band `width` pixels wide over `frame_count`."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.toast": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 152,
   "isInit": false,
   "ghost": false,
   "doc": "A small, self-dismissing notice in the bottom-right corner of its parent.",
   "annotation": "",
   "external": [
    "PySide6",
    "contextlib"
   ],
   "symbols": [
    {
     "name": "Toast",
     "kind": "class",
     "line": 50,
     "loc": 102,
     "doc": "A transient notice anchored to the bottom-right of `parent`."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.transport.__init__": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 25,
   "isInit": true,
   "ghost": false,
   "doc": "How a frame is asked for and how it arrives: request, decode, cache, pace.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.gui.transport.coalescer": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 226,
   "isInit": false,
   "ghost": false,
   "doc": "One frame request in flight, one waiting, everything between discarded.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "time"
   ],
   "symbols": [
    {
     "name": "Request",
     "kind": "class",
     "line": 48,
     "loc": 13,
     "doc": "One decode request."
    },
    {
     "name": "Arrival",
     "kind": "class",
     "line": 64,
     "loc": 15,
     "doc": "What to do with a frame that has just come back."
    },
    {
     "name": "_outranks",
     "kind": "function",
     "line": 81,
     "loc": 3,
     "doc": "Whether a new intent of `kind` may take the pending slot from `pending`."
    },
    {
     "name": "RequestCoalescer",
     "kind": "class",
     "line": 86,
     "loc": 140,
     "doc": "The two slots, the sequence counters, and the generation stamp."
    }
   ],
   "calls": [
    [
     "Arrival",
     "Request"
    ],
    [
     "_outranks",
     "Request"
    ],
    [
     "RequestCoalescer",
     "Arrival"
    ],
    [
     "RequestCoalescer",
     "Request"
    ],
    [
     "RequestCoalescer",
     "_outranks"
    ]
   ],
   "uses": [
    [
     "Request",
     "sieve.core.request_intent",
     "RequestKind"
    ],
    [
     "_outranks",
     "sieve.core.request_intent",
     "RequestKind"
    ],
    [
     "RequestCoalescer",
     "sieve.core.request_intent",
     "RequestKind"
    ]
   ]
  },
  "sieve.gui.transport.decode_worker": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 154,
   "isInit": false,
   "ghost": false,
   "doc": "The decode thread: a `VideoReader` that never blocks the event loop.",
   "annotation": "",
   "external": [
    "PySide6",
    "pathlib"
   ],
   "symbols": [
    {
     "name": "DecodeWorker",
     "kind": "class",
     "line": 42,
     "loc": 112,
     "doc": "Lives on the decode thread. Every slot here runs off the GUI thread."
    }
   ],
   "calls": [],
   "uses": [
    [
     "DecodeWorker",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "DecodeWorker",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "DecodeWorker",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "DecodeWorker",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "DecodeWorker",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ]
   ]
  },
  "sieve.gui.transport.pacing": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 74,
   "isInit": false,
   "ghost": false,
   "doc": "Where playback goes next, and how far it may go while a render is filling.",
   "annotation": "",
   "external": [
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "feed_bounds",
     "kind": "function",
     "line": 22,
     "loc": 18,
     "doc": "What playback may cover while a render is filling: up to its frontier."
    },
    {
     "name": "PlaybackStep",
     "kind": "class",
     "line": 43,
     "loc": 11,
     "doc": "Where playback goes next, and whether the clock has to be re-anchored."
    },
    {
     "name": "playback_step",
     "kind": "function",
     "line": 56,
     "loc": 18,
     "doc": "Fold a wall-clock target into `[start, stop)`, looping at the end."
    }
   ],
   "calls": [
    [
     "playback_step",
     "PlaybackStep"
    ]
   ],
   "uses": [
    [
     "feed_bounds",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "playback_step",
     "sieve.core.pipeline_model",
     "ClipRange"
    ]
   ]
  },
  "sieve.gui.transport.player": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 613,
   "isInit": false,
   "ghost": false,
   "doc": "Playback and seek control on the GUI thread.",
   "annotation": "",
   "external": [
    "PySide6",
    "time"
   ],
   "symbols": [
    {
     "name": "VideoPlayer",
     "kind": "class",
     "line": 93,
     "loc": 520,
     "doc": "Owns the decode thread and the transport state for one video."
    }
   ],
   "calls": [],
   "uses": [
    [
     "VideoPlayer",
     "sieve.bench.metrics",
     "METRICS"
    ],
    [
     "VideoPlayer",
     "sieve.bench.metrics",
     "MetricBus"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "AccessEvent"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "FROM_CACHE"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "FROM_DECODE"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "FROM_RING"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "GET"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "TRACE"
    ],
    [
     "VideoPlayer",
     "sieve.bench.retention_trace",
     "TraceRecorder"
    ],
    [
     "VideoPlayer",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "VideoPlayer",
     "sieve.core.request_intent",
     "RequestKind"
    ],
    [
     "VideoPlayer",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "VideoPlayer",
     "sieve.gui.preferences",
     "Preferences"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.coalescer",
     "Request"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.coalescer",
     "RequestCoalescer"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.decode_worker",
     "DecodeWorker"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.pacing",
     "feed_bounds"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.pacing",
     "playback_step"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.proxy_cache",
     "ProxyFrameCache"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.render_ring",
     "RenderFrameRing"
    ],
    [
     "VideoPlayer",
     "sieve.gui.transport.scrub_policy",
     "ScrubPolicy"
    ],
    [
     "VideoPlayer",
     "sieve.mutual.pool_meter",
     "PoolMeter"
    ],
    [
     "VideoPlayer",
     "sieve.mutual.shares",
     "PROXY_CACHE_SHARE"
    ],
    [
     "VideoPlayer",
     "sieve.mutual.shares",
     "resolved_bytes"
    ]
   ]
  },
  "sieve.gui.transport.proxy_cache": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 89,
   "isInit": false,
   "ghost": false,
   "doc": "A bounded LRU of decoded display proxies, keyed by frame index.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections"
   ],
   "symbols": [
    {
     "name": "ProxyFrameCache",
     "kind": "class",
     "line": 37,
     "loc": 52,
     "doc": "Least-recently-used cache of display-proxy `QImage` by frame index."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.gui.transport.render_ring": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 161,
   "isInit": false,
   "ghost": false,
   "doc": "The render's recent source frames, kept as display proxies for the player.",
   "annotation": "",
   "external": [
    "PySide6",
    "numpy",
    "threading"
   ],
   "symbols": [
    {
     "name": "RenderFrameRing",
     "kind": "class",
     "line": 68,
     "loc": 93,
     "doc": "Bounded, lock-guarded ring of the render's source frames as gray proxies."
    }
   ],
   "calls": [],
   "uses": [
    [
     "RenderFrameRing",
     "sieve.bench.retention_trace",
     "AccessEvent"
    ],
    [
     "RenderFrameRing",
     "sieve.bench.retention_trace",
     "PUT"
    ],
    [
     "RenderFrameRing",
     "sieve.bench.retention_trace",
     "TRACE"
    ],
    [
     "RenderFrameRing",
     "sieve.bench.retention_trace",
     "TraceRecorder"
    ],
    [
     "RenderFrameRing",
     "sieve.bench.retention_trace",
     "UNKNOWN_PLAYHEAD"
    ],
    [
     "RenderFrameRing",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "RenderFrameRing",
     "sieve.core.types",
     "Frame"
    ],
    [
     "RenderFrameRing",
     "sieve.gui.transport.decode_worker",
     "PROXY_WIDTH"
    ],
    [
     "RenderFrameRing",
     "sieve.gui.transport.proxy_cache",
     "ProxyFrameCache"
    ],
    [
     "RenderFrameRing",
     "sieve.mutual.shares",
     "RENDER_RING_SHARE"
    ],
    [
     "RenderFrameRing",
     "sieve.mutual.shares",
     "resolved_bytes"
    ]
   ]
  },
  "sieve.gui.transport.scrub_policy": {
   "package": "sieve.gui.transport",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 146,
   "isInit": false,
   "ghost": false,
   "doc": "When to stop decoding every scrub target, and what to decode instead.",
   "annotation": "",
   "external": [
    "collections",
    "enum",
    "statistics"
   ],
   "symbols": [
    {
     "name": "ScrubMode",
     "kind": "class",
     "line": 47,
     "loc": 5,
     "doc": "Whether a drag position means a frame or a neighbourhood."
    },
    {
     "name": "ScrubPolicy",
     "kind": "class",
     "line": 54,
     "loc": 92,
     "doc": "Decides the mode, and snaps drag targets to the grid while degraded."
    }
   ],
   "calls": [
    [
     "ScrubPolicy",
     "ScrubMode"
    ]
   ],
   "uses": []
  },
  "sieve.gui.video_view": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 762,
   "isInit": false,
   "ghost": false,
   "doc": "Frame display with the four crop gestures: draw, stamp, move, and resize.",
   "annotation": "",
   "external": [
    "PySide6",
    "dataclasses",
    "enum"
   ],
   "symbols": [
    {
     "name": "CropMode",
     "kind": "class",
     "line": 100,
     "loc": 5,
     "doc": "Whether a click on empty space draws a new box or places a stamp."
    },
    {
     "name": "Handle",
     "kind": "class",
     "line": 107,
     "loc": 11,
     "doc": "The eight grab points on the selected box."
    },
    {
     "name": "_Adjustment",
     "kind": "class",
     "line": 146,
     "loc": 21,
     "doc": "A live move or resize of one existing box."
    },
    {
     "name": "VideoView",
     "kind": "class",
     "line": 169,
     "loc": 593,
     "doc": "Letterboxed frame viewport that draws, places, and adjusts regions."
    }
   ],
   "calls": [
    [
     "_Adjustment",
     "Handle"
    ],
    [
     "VideoView",
     "CropMode"
    ],
    [
     "VideoView",
     "Handle"
    ],
    [
     "VideoView",
     "_Adjustment"
    ]
   ],
   "uses": [
    [
     "_Adjustment",
     "sieve.core.types",
     "ROI"
    ],
    [
     "VideoView",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "VideoView",
     "sieve.core.types",
     "ROI"
    ],
    [
     "VideoView",
     "sieve.gui.zoom",
     "Magnifier"
    ]
   ]
  },
  "sieve.gui.wheel_steps": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 249,
   "isInit": false,
   "ghost": false,
   "doc": "One wheel detent, one step \u2014 everywhere, accelerating through a run.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections",
    "time"
   ],
   "symbols": [
    {
     "name": "_scrollable_ancestor",
     "kind": "function",
     "line": 73,
     "loc": 29,
     "doc": "Could this wheel move something that encloses `watched`?"
    },
    {
     "name": "WheelSteps",
     "kind": "class",
     "line": 104,
     "loc": 145,
     "doc": "Application-level event filter normalizing wheel steps."
    }
   ],
   "calls": [
    [
     "WheelSteps",
     "_scrollable_ancestor"
    ]
   ],
   "uses": []
  },
  "sieve.gui.wizard": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 636,
   "isInit": false,
   "ghost": false,
   "doc": "The insert/swap wizard: the configuration surface for a provisional step.",
   "annotation": "",
   "external": [
    "PySide6",
    "numpy",
    "typing"
   ],
   "symbols": [
    {
     "name": "last_image_node_id",
     "kind": "function",
     "line": 87,
     "loc": 14,
     "doc": "The node whose output the wizard's video pane shows."
    },
    {
     "name": "frame_to_qimage",
     "kind": "function",
     "line": 103,
     "loc": 25,
     "doc": "An owning QImage of whatever an image-space node emitted."
    },
    {
     "name": "_FramePane",
     "kind": "class",
     "line": 130,
     "loc": 33,
     "doc": "The provisional chain's view of the current frame, aspect-fit."
    },
    {
     "name": "StepWizard",
     "kind": "class",
     "line": 165,
     "loc": 471,
     "doc": "The near-full-window inset a seam click or a card's swap opens."
    }
   ],
   "calls": [
    [
     "StepWizard",
     "_FramePane"
    ]
   ],
   "uses": [
    [
     "last_image_node_id",
     "sieve.gui.chain_model",
     "ChainKind"
    ],
    [
     "last_image_node_id",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "last_image_node_id",
     "sieve.gui.chain_model",
     "Status"
    ],
    [
     "last_image_node_id",
     "sieve.gui.chain_model",
     "grade"
    ],
    [
     "_FramePane",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "_FramePane",
     "sieve.gui.band_plot",
     "PANEL"
    ],
    [
     "_FramePane",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "StepWizard",
     "sieve.gui.band_plot",
     "DIM"
    ],
    [
     "StepWizard",
     "sieve.gui.band_plot",
     "LINE"
    ],
    [
     "StepWizard",
     "sieve.gui.band_plot",
     "PANEL"
    ],
    [
     "StepWizard",
     "sieve.gui.band_plot",
     "TEXT"
    ],
    [
     "StepWizard",
     "sieve.gui.band_plot",
     "plot_font"
    ],
    [
     "StepWizard",
     "sieve.gui.chain_model",
     "BLOCK_SIGNAL_ELEMENT_NAMES"
    ],
    [
     "StepWizard",
     "sieve.gui.chain_model",
     "DetectorState"
    ],
    [
     "StepWizard",
     "sieve.gui.chain_model",
     "DetectorUpdate"
    ],
    [
     "StepWizard",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "StepWizard",
     "sieve.gui.count_plot",
     "CountPlot"
    ],
    [
     "StepWizard",
     "sieve.gui.density_plot",
     "DensityPlot"
    ],
    [
     "StepWizard",
     "sieve.gui.density_plot",
     "DensitySurface"
    ],
    [
     "StepWizard",
     "sieve.gui.param_form",
     "param_rows"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "Candidate"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "CatalogEntry"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "candidates_for_insert"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "candidates_for_swap"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "guidance_for"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "insert_step"
    ],
    [
     "StepWizard",
     "sieve.gui.wizard_model",
     "swap_step"
    ]
   ]
  },
  "sieve.gui.wizard_lifecycle": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 254,
   "isInit": false,
   "ghost": false,
   "doc": "The wizard lifecycle: the open inset, session rollback, and preview mailbox.",
   "annotation": "",
   "external": [
    "PySide6",
    "collections",
    "dataclasses",
    "numpy"
   ],
   "symbols": [
    {
     "name": "WizardAccepted",
     "kind": "class",
     "line": 50,
     "loc": 5,
     "doc": "The session facts the tab needs to commit the accepted wizard."
    },
    {
     "name": "WizardCancelled",
     "kind": "class",
     "line": 58,
     "loc": 5,
     "doc": "The session facts the tab needs to roll the wizard back."
    },
    {
     "name": "WizardLifecycle",
     "kind": "class",
     "line": 65,
     "loc": 189,
     "doc": "Own the wizard session and relay every tab-owned action as a signal."
    }
   ],
   "calls": [
    [
     "WizardLifecycle",
     "WizardAccepted"
    ],
    [
     "WizardLifecycle",
     "WizardCancelled"
    ]
   ],
   "uses": [
    [
     "WizardAccepted",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "WizardCancelled",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "WizardLifecycle",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.chain_model",
     "DetectorState"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.chain_model",
     "DetectorUpdate"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.density_plot",
     "DensitySurface"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.wizard",
     "StepWizard"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.wizard",
     "frame_to_qimage"
    ],
    [
     "WizardLifecycle",
     "sieve.gui.wizard",
     "last_image_node_id"
    ]
   ]
  },
  "sieve.gui.wizard_model": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 451,
   "isInit": false,
   "ghost": false,
   "doc": "What the wizard can offer at a seam, and what each offer would do to the chain.",
   "annotation": "",
   "external": [
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "CatalogEntry",
     "kind": "class",
     "line": 59,
     "loc": 22,
     "doc": "One operation the wizard can offer."
    },
    {
     "name": "Candidate",
     "kind": "class",
     "line": 84,
     "loc": 6,
     "doc": "One catalog entry judged against one seam: offered, or refused with why."
    },
    {
     "name": "catalog",
     "kind": "function",
     "line": 125,
     "loc": 74,
     "doc": "Every operation the wizard can offer, in stage order."
    },
    {
     "name": "_summary",
     "kind": "function",
     "line": 201,
     "loc": 5,
     "doc": ""
    },
    {
     "name": "incoming_kind",
     "kind": "function",
     "line": 211,
     "loc": 13,
     "doc": "What flows into `position`, or None when a conflict above makes it unknowable."
    },
    {
     "name": "candidates_for_insert",
     "kind": "function",
     "line": 226,
     "loc": 19,
     "doc": "Every offer for inserting at `seam`, suggested stage first."
    },
    {
     "name": "candidates_for_swap",
     "kind": "function",
     "line": 247,
     "loc": 22,
     "doc": "Every offer for replacing `step_id`, its own stage first."
    },
    {
     "name": "_judge",
     "kind": "function",
     "line": 271,
     "loc": 14,
     "doc": "One entry's verdict: the duplicate rule, then the hypothetical grade."
    },
    {
     "name": "_stage_ordered",
     "kind": "function",
     "line": 287,
     "loc": 6,
     "doc": "The catalog grouped by stage with `suggested`'s group first."
    },
    {
     "name": "_seam_stage",
     "kind": "function",
     "line": 295,
     "loc": 7,
     "doc": "The stage a seam suggests: the step after it, else before, else the top."
    },
    {
     "name": "_position",
     "kind": "function",
     "line": 304,
     "loc": 5,
     "doc": ""
    },
    {
     "name": "build_step",
     "kind": "function",
     "line": 314,
     "loc": 29,
     "doc": "One fresh step from `entry`, its node minted with defaults plus `params`."
    },
    {
     "name": "_chain_scale",
     "kind": "function",
     "line": 345,
     "loc": 5,
     "doc": ""
    },
    {
     "name": "insert_step",
     "kind": "function",
     "line": 352,
     "loc": 10,
     "doc": "The chain with `entry` inserted at `seam`, and the minted step id."
    },
    {
     "name": "swap_step",
     "kind": "function",
     "line": 364,
     "loc": 25,
     "doc": "The chain with `step_id` replaced by `entry`, and the minted step id."
    },
    {
     "name": "chain_from_pipeline",
     "kind": "function",
     "line": 391,
     "loc": 50,
     "doc": "The `LiveChain` a saved graph renders as: its nodes, plus the tab-side suffix."
    },
    {
     "name": "guidance_for",
     "kind": "function",
     "line": 446,
     "loc": 5,
     "doc": "The pane's sections for `entry`: its filter's `.md`, or the inline text."
    }
   ],
   "calls": [
    [
     "Candidate",
     "CatalogEntry"
    ],
    [
     "catalog",
     "CatalogEntry"
    ],
    [
     "catalog",
     "_summary"
    ],
    [
     "candidates_for_insert",
     "Candidate"
    ],
    [
     "candidates_for_insert",
     "_judge"
    ],
    [
     "candidates_for_insert",
     "_seam_stage"
    ],
    [
     "candidates_for_insert",
     "_stage_ordered"
    ],
    [
     "candidates_for_insert",
     "incoming_kind"
    ],
    [
     "candidates_for_insert",
     "insert_step"
    ],
    [
     "candidates_for_swap",
     "Candidate"
    ],
    [
     "candidates_for_swap",
     "_judge"
    ],
    [
     "candidates_for_swap",
     "_position"
    ],
    [
     "candidates_for_swap",
     "_stage_ordered"
    ],
    [
     "candidates_for_swap",
     "incoming_kind"
    ],
    [
     "candidates_for_swap",
     "swap_step"
    ],
    [
     "_judge",
     "Candidate"
    ],
    [
     "_judge",
     "CatalogEntry"
    ],
    [
     "_stage_ordered",
     "CatalogEntry"
    ],
    [
     "_stage_ordered",
     "catalog"
    ],
    [
     "build_step",
     "CatalogEntry"
    ],
    [
     "build_step",
     "_chain_scale"
    ],
    [
     "insert_step",
     "CatalogEntry"
    ],
    [
     "insert_step",
     "build_step"
    ],
    [
     "swap_step",
     "CatalogEntry"
    ],
    [
     "swap_step",
     "_position"
    ],
    [
     "swap_step",
     "build_step"
    ],
    [
     "chain_from_pipeline",
     "catalog"
    ],
    [
     "guidance_for",
     "CatalogEntry"
    ]
   ],
   "uses": [
    [
     "CatalogEntry",
     "sieve.gui.chain_model",
     "ChainKind"
    ],
    [
     "CatalogEntry",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "catalog",
     "sieve.filters.__init__",
     "discover"
    ],
    [
     "catalog",
     "sieve.gui.chain_model",
     "ChainKind"
    ],
    [
     "catalog",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "_summary",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "_summary",
     "sieve.core.filter_registry",
     "UnknownFilterError"
    ],
    [
     "incoming_kind",
     "sieve.gui.chain_model",
     "ChainKind"
    ],
    [
     "incoming_kind",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "candidates_for_insert",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "candidates_for_swap",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "_judge",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "_judge",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "_judge",
     "sieve.gui.chain_model",
     "Status"
    ],
    [
     "_judge",
     "sieve.gui.chain_model",
     "grade"
    ],
    [
     "_stage_ordered",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "_seam_stage",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "_seam_stage",
     "sieve.gui.chain_model",
     "Stage"
    ],
    [
     "_position",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "build_step",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "build_step",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "build_step",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "build_step",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "_chain_scale",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "insert_step",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "swap_step",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "chain_from_pipeline",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "chain_from_pipeline",
     "sieve.gui.chain_model",
     "ChainStep"
    ],
    [
     "chain_from_pipeline",
     "sieve.gui.chain_model",
     "DetectorState"
    ],
    [
     "chain_from_pipeline",
     "sieve.gui.chain_model",
     "LiveChain"
    ],
    [
     "chain_from_pipeline",
     "sieve.pipeline.dag",
     "linear_order"
    ],
    [
     "guidance_for",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "guidance_for",
     "sieve.filters.__init__",
     "Guidance"
    ],
    [
     "guidance_for",
     "sieve.filters.__init__",
     "guidance_for"
    ]
   ]
  },
  "sieve.gui.zoom": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 132,
   "isInit": false,
   "ghost": false,
   "doc": "The magnifier: zoom, a pan centre, and the two rectangles between them.",
   "annotation": "",
   "external": [
    "PySide6"
   ],
   "symbols": [
    {
     "name": "Magnifier",
     "kind": "class",
     "line": 43,
     "loc": 89,
     "doc": "A zoom level and a pan centre in normalized content coordinates."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.mutual.__init__": {
   "package": "sieve.mutual",
   "layerPackage": "sieve.mutual",
   "band": 5,
   "loc": 2,
   "isInit": true,
   "ghost": false,
   "doc": "Dependency-shared resource readings and declarations.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.mutual.machine": {
   "package": "sieve.mutual",
   "layerPackage": "sieve.mutual",
   "band": 5,
   "loc": 406,
   "isInit": false,
   "ghost": false,
   "doc": "The machine is read once. Both resources, one home, importable headless.",
   "annotation": "",
   "external": [
    "collections",
    "ctypes",
    "os",
    "pathlib",
    "psutil",
    "sys"
   ],
   "symbols": [
    {
     "name": "available_cpu_ids",
     "kind": "function",
     "line": 63,
     "loc": 21,
     "doc": "Logical CPU ids this process may run on, ascending."
    },
    {
     "name": "available_cpus",
     "kind": "function",
     "line": 86,
     "loc": 15,
     "doc": "CPUs this process may actually use, not the ones the machine has."
    },
    {
     "name": "cpu_classes",
     "kind": "function",
     "line": 103,
     "loc": 25,
     "doc": "Performance class of each CPU in this process's allocation."
    },
    {
     "name": "_published_cpu_classes",
     "kind": "function",
     "line": 130,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "_windows_cpu_classes",
     "kind": "function",
     "line": 136,
     "loc": 37,
     "doc": "`GetSystemCpuSetInformation`'s efficiency class, per logical processor."
    },
    {
     "name": "linux_cpu_classes",
     "kind": "function",
     "line": 175,
     "loc": 31,
     "doc": "`cpu_capacity` ranked into ordinal classes, for big.LITTLE and friends."
    },
    {
     "name": "available_memory",
     "kind": "function",
     "line": 208,
     "loc": 30,
     "doc": "Bytes this process may hold before something kills or pages it."
    },
    {
     "name": "_cgroup_memory_limit",
     "kind": "function",
     "line": 240,
     "loc": 39,
     "doc": "The tightest memory limit any enclosing cgroup imposes, or None."
    },
    {
     "name": "_read_limit_file",
     "kind": "function",
     "line": 281,
     "loc": 12,
     "doc": "The limit a cgroup file states, as a zero-or-one element list."
    },
    {
     "name": "_scheduler_memory_limit",
     "kind": "function",
     "line": 295,
     "loc": 15,
     "doc": "What the scheduler says the job step may hold, or None."
    },
    {
     "name": "_parse_slurm_megabytes",
     "kind": "function",
     "line": 312,
     "loc": 12,
     "doc": "A Slurm memory value in bytes: digits, optionally suffixed K/M/G/T."
    },
    {
     "name": "MemoryUnreadableError",
     "kind": "class",
     "line": 326,
     "loc": 9,
     "doc": "A session memory reading that could not be taken honestly."
    },
    {
     "name": "process_memory_bytes",
     "kind": "function",
     "line": 337,
     "loc": 34,
     "doc": "Resident bytes of this process and every live child, summed."
    },
    {
     "name": "physical_memory",
     "kind": "function",
     "line": 373,
     "loc": 33,
     "doc": "The machine's installed RAM \u2014 the last resort, and the desktop answer."
    }
   ],
   "calls": [
    [
     "available_cpus",
     "available_cpu_ids"
    ],
    [
     "cpu_classes",
     "_published_cpu_classes"
    ],
    [
     "cpu_classes",
     "available_cpu_ids"
    ],
    [
     "_published_cpu_classes",
     "_windows_cpu_classes"
    ],
    [
     "_published_cpu_classes",
     "linux_cpu_classes"
    ],
    [
     "available_memory",
     "_cgroup_memory_limit"
    ],
    [
     "available_memory",
     "_scheduler_memory_limit"
    ],
    [
     "available_memory",
     "physical_memory"
    ],
    [
     "_cgroup_memory_limit",
     "_read_limit_file"
    ],
    [
     "_scheduler_memory_limit",
     "_parse_slurm_megabytes"
    ],
    [
     "_scheduler_memory_limit",
     "available_cpus"
    ],
    [
     "process_memory_bytes",
     "MemoryUnreadableError"
    ]
   ],
   "uses": []
  },
  "sieve.mutual.pool_meter": {
   "package": "sieve.mutual",
   "layerPackage": "sieve.mutual",
   "band": 5,
   "loc": 91,
   "isInit": false,
   "ghost": false,
   "doc": "The counters a worker pool exposes so its utilisation stops being a guess.",
   "annotation": "",
   "external": [
    "collections",
    "contextlib",
    "threading",
    "time"
   ],
   "symbols": [
    {
     "name": "PoolMeter",
     "kind": "class",
     "line": 46,
     "loc": 45,
     "doc": "Busy time and queue depth for one worker pool, read by a sampler."
    }
   ],
   "calls": [],
   "uses": []
  },
  "sieve.mutual.shares": {
   "package": "sieve.mutual",
   "layerPackage": "sieve.mutual",
   "band": 5,
   "loc": 187,
   "isInit": false,
   "ghost": false,
   "doc": "How a session divides the machine among threads and bytes: one table,",
   "annotation": "",
   "external": [
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "WorkerSplit",
     "kind": "class",
     "line": 54,
     "loc": 8,
     "doc": ""
    },
    {
     "name": "MemoryShare",
     "kind": "class",
     "line": 79,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "memory_reserve",
     "kind": "function",
     "line": 163,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "memory_budget",
     "kind": "function",
     "line": 168,
     "loc": 3,
     "doc": ""
    },
    {
     "name": "resolved_bytes",
     "kind": "function",
     "line": 173,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "ledger_ceiling",
     "kind": "function",
     "line": 177,
     "loc": 4,
     "doc": ""
    },
    {
     "name": "fits_memory",
     "kind": "function",
     "line": 183,
     "loc": 4,
     "doc": ""
    }
   ],
   "calls": [
    [
     "memory_budget",
     "memory_reserve"
    ],
    [
     "resolved_bytes",
     "MemoryShare"
    ],
    [
     "resolved_bytes",
     "memory_budget"
    ],
    [
     "ledger_ceiling",
     "memory_reserve"
    ],
    [
     "ledger_ceiling",
     "resolved_bytes"
    ],
    [
     "fits_memory",
     "memory_reserve"
    ]
   ],
   "uses": [
    [
     "memory_budget",
     "sieve.mutual.machine",
     "available_memory"
    ],
    [
     "ledger_ceiling",
     "sieve.mutual.machine",
     "available_memory"
    ],
    [
     "fits_memory",
     "sieve.mutual.machine",
     "available_memory"
    ]
   ]
  },
  "sieve.pipeline.__init__": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 7,
   "isInit": true,
   "ghost": false,
   "doc": "Orchestration: what runs, in what order, and what may be reused.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.pipeline.cache": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 115,
   "isInit": false,
   "ghost": false,
   "doc": "Where a computed frame is kept so it is not computed twice.",
   "annotation": "",
   "external": [
    "typing"
   ],
   "symbols": [
    {
     "name": "FrameStore",
     "kind": "class",
     "line": 40,
     "loc": 28,
     "doc": "Somewhere a computed frame can be put and later found."
    },
    {
     "name": "MemoryFrameStore",
     "kind": "class",
     "line": 70,
     "loc": 28,
     "doc": "The whole cache in a dict, for one process, for as long as it lives."
    },
    {
     "name": "NullFrameStore",
     "kind": "class",
     "line": 100,
     "loc": 15,
     "doc": "A store that keeps nothing, so every lookup misses."
    }
   ],
   "calls": [],
   "uses": [
    [
     "FrameStore",
     "sieve.core.types",
     "Frame"
    ],
    [
     "FrameStore",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "MemoryFrameStore",
     "sieve.core.types",
     "Frame"
    ],
    [
     "MemoryFrameStore",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "NullFrameStore",
     "sieve.core.types",
     "Frame"
    ],
    [
     "NullFrameStore",
     "sieve.core.types",
     "FrameIndex"
    ]
   ]
  },
  "sieve.pipeline.cache_key": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 329,
   "isInit": false,
   "ghost": false,
   "doc": "What makes two computations the same computation.",
   "annotation": "",
   "external": [
    "collections",
    "enum",
    "hashlib",
    "json",
    "pathlib"
   ],
   "symbols": [
    {
     "name": "NotCacheableError",
     "kind": "class",
     "line": 92,
     "loc": 11,
     "doc": "A key was requested for a filter whose output cannot be safely keyed."
    },
    {
     "name": "CachePolicy",
     "kind": "class",
     "line": 105,
     "loc": 7,
     "doc": "The cache-key layer's decision from spec facts and the cache contract."
    },
    {
     "name": "cache_policy",
     "kind": "function",
     "line": 114,
     "loc": 15,
     "doc": "Whether this spec may have a node key under the current cache contract."
    },
    {
     "name": "is_cacheable",
     "kind": "function",
     "line": 131,
     "loc": 3,
     "doc": "Whether `node_key` will derive a key for `spec`."
    },
    {
     "name": "_uncacheable_clause",
     "kind": "function",
     "line": 136,
     "loc": 17,
     "doc": "Why the refusal happened, said off `cache_policy` and not off the spec."
    },
    {
     "name": "_digest",
     "kind": "function",
     "line": 155,
     "loc": 11,
     "doc": "Hash a fixed-arity list of JSON-representable parts."
    },
    {
     "name": "source_identity",
     "kind": "function",
     "line": 168,
     "loc": 23,
     "doc": "A string that changes when the footage at `video` changes."
    },
    {
     "name": "source_key",
     "kind": "function",
     "line": 193,
     "loc": 69,
     "doc": "The key for frames as one replicate sees them: the ancestor of every root."
    },
    {
     "name": "node_key",
     "kind": "function",
     "line": 264,
     "loc": 65,
     "doc": "The key for `node`'s output, for one replicate, on one backend."
    }
   ],
   "calls": [
    [
     "cache_policy",
     "CachePolicy"
    ],
    [
     "is_cacheable",
     "CachePolicy"
    ],
    [
     "is_cacheable",
     "cache_policy"
    ],
    [
     "_uncacheable_clause",
     "CachePolicy"
    ],
    [
     "_uncacheable_clause",
     "cache_policy"
    ],
    [
     "source_key",
     "_digest"
    ],
    [
     "node_key",
     "NotCacheableError"
    ],
    [
     "node_key",
     "_digest"
    ],
    [
     "node_key",
     "_uncacheable_clause"
    ],
    [
     "node_key",
     "is_cacheable"
    ]
   ],
   "uses": [
    [
     "cache_policy",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "cache_policy",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "is_cacheable",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_uncacheable_clause",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "source_key",
     "sieve.core.types",
     "ROI"
    ],
    [
     "source_key",
     "sieve.decode.identity",
     "decoder_identity"
    ],
    [
     "source_key",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "node_key",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "node_key",
     "sieve.backend.identity",
     "backend_identity"
    ],
    [
     "node_key",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "node_key",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "node_key",
     "sieve.core.pipeline_model",
     "resolved_params"
    ],
    [
     "node_key",
     "sieve.core.replicates",
     "Replicate"
    ]
   ]
  },
  "sieve.pipeline.crop_binding": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 277,
   "isInit": false,
   "ghost": false,
   "doc": "Which record backs a replicate right now, and why one stopped.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "enum",
    "pathlib"
   ],
   "symbols": [
    {
     "name": "CropState",
     "kind": "class",
     "line": 65,
     "loc": 18,
     "doc": "The four states the source card renders."
    },
    {
     "name": "CropBacking",
     "kind": "class",
     "line": 86,
     "loc": 16,
     "doc": "What one replicate's source boundary is, in one value."
    },
    {
     "name": "ArtifactEvidence",
     "kind": "class",
     "line": 105,
     "loc": 21,
     "doc": "What is behind a record, as the directory entry has it rather than as the"
    },
    {
     "name": "evidence_for",
     "kind": "function",
     "line": 128,
     "loc": 15,
     "doc": "What is actually on disk behind `artifact`."
    },
    {
     "name": "backing_for",
     "kind": "function",
     "line": 145,
     "loc": 65,
     "doc": "The state of `replicates[index]`'s source boundary."
    },
    {
     "name": "_near_miss",
     "kind": "function",
     "line": 212,
     "loc": 33,
     "doc": "A record cut at this exact box that has stopped matching, and why."
    },
    {
     "name": "_orphan_for",
     "kind": "function",
     "line": 247,
     "loc": 20,
     "doc": "The unclaimed record this replicate \u2014 and only this one \u2014 overlaps."
    },
    {
     "name": "_overlaps",
     "kind": "function",
     "line": 269,
     "loc": 8,
     "doc": "Whether two regions share a pixel."
    }
   ],
   "calls": [
    [
     "CropBacking",
     "CropState"
    ],
    [
     "evidence_for",
     "ArtifactEvidence"
    ],
    [
     "backing_for",
     "CropBacking"
    ],
    [
     "backing_for",
     "CropState"
    ],
    [
     "backing_for",
     "_near_miss"
    ],
    [
     "backing_for",
     "_orphan_for"
    ],
    [
     "_near_miss",
     "CropBacking"
    ],
    [
     "_near_miss",
     "CropState"
    ],
    [
     "_orphan_for",
     "_overlaps"
    ]
   ],
   "uses": [
    [
     "CropBacking",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "evidence_for",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "backing_for",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "backing_for",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "backing_for",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "backing_for",
     "sieve.pipeline.source_home",
     "SourceHome"
    ],
    [
     "_near_miss",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "_near_miss",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_orphan_for",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "_orphan_for",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_overlaps",
     "sieve.core.types",
     "ROI"
    ]
   ]
  },
  "sieve.pipeline.dag": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 908,
   "isInit": false,
   "ghost": false,
   "doc": "The graph, resolved: what runs, in what order, and whether it can run at all.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "GraphError",
     "kind": "class",
     "line": 86,
     "loc": 10,
     "doc": "A pipeline that cannot be executed as written."
    },
    {
     "name": "UnresolvedFilterError",
     "kind": "class",
     "line": 98,
     "loc": 15,
     "doc": "One or more nodes name a filter this build does not have."
    },
    {
     "name": "CycleError",
     "kind": "class",
     "line": 115,
     "loc": 13,
     "doc": "The graph contains a cycle, so no node in it can be ordered."
    },
    {
     "name": "PortWiringError",
     "kind": "class",
     "line": 130,
     "loc": 14,
     "doc": "A node's incoming edges do not line up with its declared input ports."
    },
    {
     "name": "EdgeTypeError",
     "kind": "class",
     "line": 146,
     "loc": 19,
     "doc": "An edge carries something its downstream's port cannot consume."
    },
    {
     "name": "Diagnostic",
     "kind": "class",
     "line": 168,
     "loc": 23,
     "doc": "One rejection, addressed to the nodes it is about."
    },
    {
     "name": "Dag",
     "kind": "class",
     "line": 194,
     "loc": 639,
     "doc": "A `Pipeline` whose filters resolve, whose edges chain, and which sorts."
    },
    {
     "name": "linear_order",
     "kind": "function",
     "line": 835,
     "loc": 31,
     "doc": "The pipeline's nodes root to sink, refusing anything but one path."
    },
    {
     "name": "graph_needs_chroma",
     "kind": "function",
     "line": 868,
     "loc": 22,
     "doc": "`Dag.needs_chroma` for a graph nobody has built a `Dag` from yet."
    },
    {
     "name": "_requires_chroma",
     "kind": "function",
     "line": 892,
     "loc": 16,
     "doc": "Whether `spec` refuses a single-channel frame."
    }
   ],
   "calls": [
    [
     "UnresolvedFilterError",
     "GraphError"
    ],
    [
     "CycleError",
     "GraphError"
    ],
    [
     "PortWiringError",
     "GraphError"
    ],
    [
     "EdgeTypeError",
     "GraphError"
    ],
    [
     "Diagnostic",
     "GraphError"
    ],
    [
     "Dag",
     "CycleError"
    ],
    [
     "Dag",
     "Diagnostic"
    ],
    [
     "Dag",
     "EdgeTypeError"
    ],
    [
     "Dag",
     "PortWiringError"
    ],
    [
     "Dag",
     "UnresolvedFilterError"
    ],
    [
     "Dag",
     "_requires_chroma"
    ],
    [
     "linear_order",
     "GraphError"
    ],
    [
     "graph_needs_chroma",
     "Dag"
    ],
    [
     "graph_needs_chroma",
     "GraphError"
    ]
   ],
   "uses": [
    [
     "EdgeTypeError",
     "sieve.core.filter_base",
     "StreamSpec"
    ],
    [
     "Dag",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "Dag",
     "sieve.core.filter_base",
     "ElementKind"
    ],
    [
     "Dag",
     "sieve.core.filter_base",
     "ElementNames"
    ],
    [
     "Dag",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "Dag",
     "sieve.core.filter_base",
     "SOURCE_ELEMENT_NAMES"
    ],
    [
     "Dag",
     "sieve.core.filter_base",
     "node_element"
    ],
    [
     "Dag",
     "sieve.core.filter_base",
     "node_element_names"
    ],
    [
     "Dag",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "Dag",
     "sieve.core.filter_registry",
     "REGISTRY"
    ],
    [
     "Dag",
     "sieve.core.filter_registry",
     "UnknownFilterError"
    ],
    [
     "Dag",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "Dag",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "Dag",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "Dag",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "Dag",
     "sieve.pipeline.cache_key",
     "NotCacheableError"
    ],
    [
     "Dag",
     "sieve.pipeline.cache_key",
     "node_key"
    ],
    [
     "Dag",
     "sieve.pipeline.cache_key",
     "source_key"
    ],
    [
     "linear_order",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "linear_order",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "graph_needs_chroma",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "graph_needs_chroma",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "_requires_chroma",
     "sieve.core.filter_base",
     "ArraySpec"
    ],
    [
     "_requires_chroma",
     "sieve.core.filter_base",
     "FilterSpec"
    ],
    [
     "_requires_chroma",
     "sieve.core.types",
     "ChannelSpec"
    ]
   ]
  },
  "sieve.pipeline.executor": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 429,
   "isInit": false,
   "ghost": false,
   "doc": "The single shared execution path: a plan, a reader, and a store go in.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "typing"
   ],
   "symbols": [
    {
     "name": "FormatMismatchError",
     "kind": "class",
     "line": 78,
     "loc": 9,
     "doc": "The reader's decode format is not the one this run's keys were derived"
    },
    {
     "name": "UnrunnableNodeError",
     "kind": "class",
     "line": 89,
     "loc": 15,
     "doc": "A node this graph contains cannot be executed by this executor."
    },
    {
     "name": "FrameSource",
     "kind": "class",
     "line": 106,
     "loc": 13,
     "doc": "Random access to source frames by index."
    },
    {
     "name": "FrameResult",
     "kind": "class",
     "line": 122,
     "loc": 61,
     "doc": "Every node's output for one source frame."
    },
    {
     "name": "BoundNode",
     "kind": "class",
     "line": 186,
     "loc": 6,
     "doc": "A selected kernel plus the call shape its spec requires."
    },
    {
     "name": "execute",
     "kind": "function",
     "line": 194,
     "loc": 97,
     "doc": "Run `plan` against `reader`, yielding one result per frame of the span."
    },
    {
     "name": "_check_format",
     "kind": "function",
     "line": 293,
     "loc": 24,
     "doc": "Refuse a reader whose format is not the one the keys were derived under."
    },
    {
     "name": "_bind",
     "kind": "function",
     "line": 319,
     "loc": 42,
     "doc": "Resolve every node to the callable that implements it, or refuse."
    },
    {
     "name": "_crop",
     "kind": "function",
     "line": 363,
     "loc": 14,
     "doc": "The replicate's region of `frame`, clamped to what was decoded."
    },
    {
     "name": "_run_node",
     "kind": "function",
     "line": 379,
     "loc": 50,
     "doc": "One kernel call, with the frame index checked on the way out."
    }
   ],
   "calls": [
    [
     "execute",
     "FrameResult"
    ],
    [
     "execute",
     "FrameSource"
    ],
    [
     "execute",
     "_bind"
    ],
    [
     "execute",
     "_check_format"
    ],
    [
     "execute",
     "_crop"
    ],
    [
     "execute",
     "_run_node"
    ],
    [
     "_check_format",
     "FormatMismatchError"
    ],
    [
     "_bind",
     "BoundNode"
    ],
    [
     "_bind",
     "UnrunnableNodeError"
    ],
    [
     "_run_node",
     "BoundNode"
    ],
    [
     "_run_node",
     "UnrunnableNodeError"
    ]
   ],
   "uses": [
    [
     "FrameSource",
     "sieve.core.types",
     "Frame"
    ],
    [
     "FrameResult",
     "sieve.core.types",
     "Frame"
    ],
    [
     "FrameResult",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "BoundNode",
     "sieve.backend.dispatch",
     "Kernel"
    ],
    [
     "BoundNode",
     "sieve.backend.dispatch",
     "MergingKernel"
    ],
    [
     "BoundNode",
     "sieve.backend.dispatch",
     "WindowedKernel"
    ],
    [
     "BoundNode",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "execute",
     "sieve.backend.dispatch",
     "KERNELS"
    ],
    [
     "execute",
     "sieve.backend.dispatch",
     "KernelRegistry"
    ],
    [
     "execute",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "execute",
     "sieve.core.types",
     "Frame"
    ],
    [
     "execute",
     "sieve.pipeline.cache",
     "FrameStore"
    ],
    [
     "execute",
     "sieve.pipeline.cache",
     "NullFrameStore"
    ],
    [
     "execute",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_check_format",
     "sieve.core.types",
     "ChannelSpec"
    ],
    [
     "_check_format",
     "sieve.core.types",
     "Frame"
    ],
    [
     "_check_format",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_bind",
     "sieve.backend.dispatch",
     "KernelRegistry"
    ],
    [
     "_bind",
     "sieve.backend.dispatch",
     "unrunnable_reason"
    ],
    [
     "_bind",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "_bind",
     "sieve.core.filter_base",
     "node_warmup_frames"
    ],
    [
     "_bind",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_crop",
     "sieve.core.types",
     "Frame"
    ],
    [
     "_crop",
     "sieve.core.types",
     "ROI"
    ],
    [
     "_run_node",
     "sieve.core.filter_base",
     "Mode"
    ],
    [
     "_run_node",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "_run_node",
     "sieve.core.types",
     "Frame"
    ],
    [
     "_run_node",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "_run_node",
     "sieve.core.types",
     "FrameSpan"
    ],
    [
     "_run_node",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ]
   ]
  },
  "sieve.pipeline.lowering": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 216,
   "isInit": false,
   "ghost": false,
   "doc": "Recognize the one root prefix safe to lower into an FFmpeg source.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "json",
    "typing"
   ],
   "symbols": [
    {
     "name": "LoweredGraph",
     "kind": "class",
     "line": 20,
     "loc": 6,
     "doc": "A DAG whose root prefix has moved into the source contract."
    },
    {
     "name": "lower_resolved_source",
     "kind": "function",
     "line": 28,
     "loc": 23,
     "doc": "Return `dag` and `resolved`, lowered when the safe prefix exists."
    },
    {
     "name": "lower_root_prefix",
     "kind": "function",
     "line": 53,
     "loc": 73,
     "doc": "Lower a source-space crop plus one area scale, or decline."
    },
    {
     "name": "_is",
     "kind": "function",
     "line": 128,
     "loc": 2,
     "doc": ""
    },
    {
     "name": "_single_child",
     "kind": "function",
     "line": 132,
     "loc": 8,
     "doc": ""
    },
    {
     "name": "_scale",
     "kind": "function",
     "line": 142,
     "loc": 37,
     "doc": ""
    },
    {
     "name": "_can_remove",
     "kind": "function",
     "line": 181,
     "loc": 14,
     "doc": ""
    },
    {
     "name": "_without_nodes",
     "kind": "function",
     "line": 197,
     "loc": 10,
     "doc": ""
    },
    {
     "name": "_roi_json",
     "kind": "function",
     "line": 209,
     "loc": 7,
     "doc": ""
    }
   ],
   "calls": [
    [
     "lower_resolved_source",
     "lower_root_prefix"
    ],
    [
     "lower_root_prefix",
     "LoweredGraph"
    ],
    [
     "lower_root_prefix",
     "_can_remove"
    ],
    [
     "lower_root_prefix",
     "_is"
    ],
    [
     "lower_root_prefix",
     "_roi_json"
    ],
    [
     "lower_root_prefix",
     "_scale"
    ],
    [
     "lower_root_prefix",
     "_single_child"
    ],
    [
     "lower_root_prefix",
     "_without_nodes"
    ],
    [
     "_scale",
     "_is"
    ]
   ],
   "uses": [
    [
     "LoweredGraph",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "LoweredGraph",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "lower_resolved_source",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "lower_resolved_source",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "lower_resolved_source",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "lower_resolved_source",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "lower_resolved_source",
     "sieve.pipeline.resolve_source",
     "ResolvedSource"
    ],
    [
     "lower_root_prefix",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "lower_root_prefix",
     "sieve.core.pipeline_model",
     "resolved_params"
    ],
    [
     "lower_root_prefix",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "lower_root_prefix",
     "sieve.core.types",
     "ROI"
    ],
    [
     "lower_root_prefix",
     "sieve.core.types",
     "VideoMetadata"
    ],
    [
     "lower_root_prefix",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "lower_root_prefix",
     "sieve.decode.lowered",
     "LoweredStep"
    ],
    [
     "lower_root_prefix",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "lower_root_prefix",
     "sieve.pipeline.dag",
     "GraphError"
    ],
    [
     "_is",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "_single_child",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "_single_child",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_scale",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "_scale",
     "sieve.core.pipeline_model",
     "resolved_params"
    ],
    [
     "_scale",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "_scale",
     "sieve.core.types",
     "ROI"
    ],
    [
     "_scale",
     "sieve.decode.lowered",
     "LoweredScale"
    ],
    [
     "_scale",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_can_remove",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_without_nodes",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "_roi_json",
     "sieve.core.types",
     "ROI"
    ],
    [
     "_roi_json",
     "sieve.decode.lowered",
     "roi_parts"
    ]
   ]
  },
  "sieve.pipeline.materialize": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 284,
   "isInit": false,
   "ghost": false,
   "doc": "Cut one replicate's crop to a file, and refuse to register one that lies.",
   "annotation": "",
   "external": [
    "collections",
    "hashlib",
    "numpy",
    "pathlib",
    "re",
    "typing"
   ],
   "symbols": [
    {
     "name": "MaterializeCancelledError",
     "kind": "class",
     "line": 75,
     "loc": 2,
     "doc": "The caller withdrew mid-write. No file is left behind."
    },
    {
     "name": "CropVerificationError",
     "kind": "class",
     "line": 79,
     "loc": 6,
     "doc": "The written file did not read back as what was fed to it."
    },
    {
     "name": "crops_dir",
     "kind": "function",
     "line": 87,
     "loc": 3,
     "doc": "The folder artifacts cut from `video` belong in. Need not exist."
    },
    {
     "name": "artifact_filename",
     "kind": "function",
     "line": 92,
     "loc": 9,
     "doc": "`<replicate slug>-<format>-<start>-<end>.mkv`."
    },
    {
     "name": "materialize_crop",
     "kind": "function",
     "line": 103,
     "loc": 75,
     "doc": "Write `replicate`'s crop of `video` over `span`, verified, and record it."
    },
    {
     "name": "_FedFrames",
     "kind": "class",
     "line": 180,
     "loc": 26,
     "doc": "The per-frame evidence the read-back pass is checked against."
    },
    {
     "name": "_cropped",
     "kind": "function",
     "line": 208,
     "loc": 21,
     "doc": "The replicate's region of every frame in `span`, in order."
    },
    {
     "name": "_verify",
     "kind": "function",
     "line": 231,
     "loc": 34,
     "doc": "Read `path` back and refuse it if it is not what was fed."
    },
    {
     "name": "_digest",
     "kind": "function",
     "line": 267,
     "loc": 3,
     "doc": "A content hash of one frame, over its bytes in C order."
    },
    {
     "name": "_relative_posix",
     "kind": "function",
     "line": 272,
     "loc": 12,
     "doc": "`target` relative to `base` as POSIX, or absolute across drives."
    }
   ],
   "calls": [
    [
     "materialize_crop",
     "_FedFrames"
    ],
    [
     "materialize_crop",
     "_cropped"
    ],
    [
     "materialize_crop",
     "_relative_posix"
    ],
    [
     "materialize_crop",
     "_verify"
    ],
    [
     "materialize_crop",
     "artifact_filename"
    ],
    [
     "materialize_crop",
     "crops_dir"
    ],
    [
     "_FedFrames",
     "_digest"
    ],
    [
     "_cropped",
     "MaterializeCancelledError"
    ],
    [
     "_verify",
     "CropVerificationError"
    ],
    [
     "_verify",
     "_FedFrames"
    ],
    [
     "_verify",
     "_digest"
    ]
   ],
   "uses": [
    [
     "artifact_filename",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "artifact_filename",
     "sieve.core.pipeline_model",
     "CropFormat"
    ],
    [
     "materialize_crop",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "materialize_crop",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "materialize_crop",
     "sieve.core.pipeline_model",
     "CropFormat"
    ],
    [
     "materialize_crop",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "materialize_crop",
     "sieve.decode.identity",
     "decoder_identity"
    ],
    [
     "materialize_crop",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "materialize_crop",
     "sieve.pipeline.cache_key",
     "source_identity"
    ],
    [
     "materialize_crop",
     "sieve.storage.crop_writer",
     "write_ffv1"
    ],
    [
     "_cropped",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "_cropped",
     "sieve.core.types",
     "ROI"
    ],
    [
     "_cropped",
     "sieve.decode.reader",
     "VideoReader"
    ],
    [
     "_verify",
     "sieve.decode.reader",
     "VideoReader"
    ]
   ]
  },
  "sieve.pipeline.plan": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 431,
   "isInit": false,
   "ghost": false,
   "doc": "Everything about a run that is knowable before a frame is decoded.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "ExecutionPlan",
     "kind": "class",
     "line": 82,
     "loc": 263,
     "doc": "One run of one graph, over one span, for one replicate, on one backend."
    },
    {
     "name": "_selected",
     "kind": "function",
     "line": 347,
     "loc": 35,
     "doc": "`requested` intersected with what every node in the graph keeps."
    },
    {
     "name": "_lead_in",
     "kind": "function",
     "line": 384,
     "loc": 25,
     "doc": "Source frames of lead-in for the whole graph."
    },
    {
     "name": "root_paths",
     "kind": "function",
     "line": 411,
     "loc": 20,
     "doc": "Every root-to-`node_id` path, inclusive at both ends."
    }
   ],
   "calls": [
    [
     "ExecutionPlan",
     "_lead_in"
    ],
    [
     "ExecutionPlan",
     "_selected"
    ]
   ],
   "uses": [
    [
     "ExecutionPlan",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "ExecutionPlan",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "ExecutionPlan",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "ExecutionPlan",
     "sieve.core.pipeline_model",
     "resolved_params"
    ],
    [
     "ExecutionPlan",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "ExecutionPlan",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "ExecutionPlan",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "ExecutionPlan",
     "sieve.core.types",
     "FrameRange"
    ],
    [
     "ExecutionPlan",
     "sieve.core.types",
     "NO_FRAMES"
    ],
    [
     "ExecutionPlan",
     "sieve.core.types",
     "ROI"
    ],
    [
     "ExecutionPlan",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "ExecutionPlan",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_selected",
     "sieve.core.filter_base",
     "ALL_FRAMES"
    ],
    [
     "_selected",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "_selected",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "_selected",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "_lead_in",
     "sieve.core.filter_base",
     "ParamsBase"
    ],
    [
     "_lead_in",
     "sieve.core.filter_base",
     "input_warmup_frames"
    ],
    [
     "_lead_in",
     "sieve.core.types",
     "FrameCount"
    ],
    [
     "_lead_in",
     "sieve.core.types",
     "NO_FRAMES"
    ],
    [
     "_lead_in",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "root_paths",
     "sieve.core.pipeline_model",
     "Node"
    ],
    [
     "root_paths",
     "sieve.pipeline.dag",
     "Dag"
    ]
   ]
  },
  "sieve.pipeline.preview": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 426,
   "isInit": false,
   "ghost": false,
   "doc": "The representative-clip preview: one window, one arena, many revisions.",
   "annotation": "",
   "external": [
    "collections",
    "contextlib",
    "dataclasses"
   ],
   "symbols": [
    {
     "name": "PreviewRender",
     "kind": "class",
     "line": 114,
     "loc": 34,
     "doc": "What one render did, in units a HUD and a gate both read."
    },
    {
     "name": "PreviewSession",
     "kind": "class",
     "line": 150,
     "loc": 245,
     "doc": "One asset, one window, one arena, one store \u2014 and a graph per render."
    },
    {
     "name": "_Tally",
     "kind": "class",
     "line": 397,
     "loc": 19,
     "doc": "Running counts over one render, so `_run` holds no frame it has passed on."
    },
    {
     "name": "_discard",
     "kind": "function",
     "line": 418,
     "loc": 8,
     "doc": "The consumer a render with no viewer uses."
    }
   ],
   "calls": [
    [
     "PreviewSession",
     "PreviewRender"
    ],
    [
     "PreviewSession",
     "_Tally"
    ],
    [
     "PreviewSession",
     "_discard"
    ]
   ],
   "uses": [
    [
     "PreviewRender",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "PreviewRender",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "PreviewSession",
     "sieve.backend.dispatch",
     "Backend"
    ],
    [
     "PreviewSession",
     "sieve.backend.dispatch",
     "KernelRegistry"
    ],
    [
     "PreviewSession",
     "sieve.core.filter_registry",
     "FilterRegistry"
    ],
    [
     "PreviewSession",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "PreviewSession",
     "sieve.core.pipeline_model",
     "Pipeline"
    ],
    [
     "PreviewSession",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "PreviewSession",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "PreviewSession",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "PreviewSession",
     "sieve.pipeline.cache",
     "FrameStore"
    ],
    [
     "PreviewSession",
     "sieve.pipeline.cache",
     "MemoryFrameStore"
    ],
    [
     "PreviewSession",
     "sieve.pipeline.dag",
     "Dag"
    ],
    [
     "PreviewSession",
     "sieve.pipeline.executor",
     "FrameSource"
    ],
    [
     "PreviewSession",
     "sieve.pipeline.executor",
     "execute"
    ],
    [
     "PreviewSession",
     "sieve.pipeline.plan",
     "ExecutionPlan"
    ],
    [
     "_Tally",
     "sieve.pipeline.executor",
     "FrameResult"
    ],
    [
     "_discard",
     "sieve.pipeline.executor",
     "FrameResult"
    ]
   ]
  },
  "sieve.pipeline.resolve_source": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 214,
   "isInit": false,
   "ghost": false,
   "doc": "Which file a replicate's run opens, and in whose frame numbering.",
   "annotation": "",
   "external": [
    "collections",
    "dataclasses",
    "pathlib"
   ],
   "symbols": [
    {
     "name": "ResolvedSource",
     "kind": "class",
     "line": 67,
     "loc": 48,
     "doc": "The file one replicate's run reads, and how to plan against it."
    },
    {
     "name": "OffsetFrameSource",
     "kind": "class",
     "line": 117,
     "loc": 36,
     "doc": "A `FrameSource` renumbered so that its frame 0 is source frame `first`."
    },
    {
     "name": "resolve",
     "kind": "function",
     "line": 155,
     "loc": 59,
     "doc": "The source `replicate`'s run over `want` should read."
    }
   ],
   "calls": [
    [
     "ResolvedSource",
     "OffsetFrameSource"
    ],
    [
     "resolve",
     "ResolvedSource"
    ]
   ],
   "uses": [
    [
     "ResolvedSource",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "ResolvedSource",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "ResolvedSource",
     "sieve.decode.lowered",
     "LoweredPrefix"
    ],
    [
     "ResolvedSource",
     "sieve.pipeline.executor",
     "FrameSource"
    ],
    [
     "OffsetFrameSource",
     "sieve.core.types",
     "Frame"
    ],
    [
     "OffsetFrameSource",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "OffsetFrameSource",
     "sieve.decode.reader",
     "VideoDecodeError"
    ],
    [
     "OffsetFrameSource",
     "sieve.pipeline.executor",
     "FrameSource"
    ],
    [
     "resolve",
     "sieve.core.pipeline_model",
     "ClipRange"
    ],
    [
     "resolve",
     "sieve.core.pipeline_model",
     "CropArtifact"
    ],
    [
     "resolve",
     "sieve.core.replicates",
     "Replicate"
    ],
    [
     "resolve",
     "sieve.core.types",
     "FrameIndex"
    ],
    [
     "resolve",
     "sieve.pipeline.cache_key",
     "source_identity"
    ],
    [
     "resolve",
     "sieve.pipeline.source_home",
     "SourceHome"
    ]
   ]
  },
  "sieve.pipeline.series_collector": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 171,
   "isInit": false,
   "ghost": false,
   "doc": "Assemble one node's per-frame outputs into a (T, ny, nx) series.",
   "annotation": "",
   "external": [
    "dataclasses",
    "numpy",
    "threading"
   ],
   "symbols": [
    {
     "name": "CollectedSeries",
     "kind": "class",
     "line": 40,
     "loc": 7,
     "doc": "One revision's assembled series, aligned to source frame indices."
    },
    {
     "name": "CollectedRows",
     "kind": "class",
     "line": 50,
     "loc": 12,
     "doc": "One revision's rows so far, unstacked \u2014 the cheap snapshot."
    },
    {
     "name": "SeriesCollector",
     "kind": "class",
     "line": 64,
     "loc": 107,
     "doc": "Rows in on the render thread, one array out on the consumer's."
    }
   ],
   "calls": [
    [
     "SeriesCollector",
     "CollectedRows"
    ],
    [
     "SeriesCollector",
     "CollectedSeries"
    ]
   ],
   "uses": [
    [
     "SeriesCollector",
     "sieve.pipeline.executor",
     "FrameResult"
    ]
   ]
  },
  "sieve.pipeline.source_home": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 62,
   "isInit": false,
   "ghost": false,
   "doc": "The frame of reference a crop record is read against: three facts, one value.",
   "annotation": "",
   "external": [
    "dataclasses",
    "pathlib"
   ],
   "symbols": [
    {
     "name": "SourceHome",
     "kind": "class",
     "line": 36,
     "loc": 26,
     "doc": "Where the footage is, what it is, and what its crops sit beside."
    }
   ],
   "calls": [],
   "uses": [
    [
     "SourceHome",
     "sieve.pipeline.cache_key",
     "source_identity"
    ]
   ]
  },
  "sieve.pipeline.upgrade": {
   "package": "sieve.pipeline",
   "layerPackage": "sieve.pipeline",
   "band": 2,
   "loc": 233,
   "isInit": false,
   "ghost": false,
   "doc": "Carry a saved document's crop and span into the graph that computes them.",
   "annotation": "",
   "external": [
    "collections",
    "typing"
   ],
   "symbols": [
    {
     "name": "UnupgradableDocumentError",
     "kind": "class",
     "line": 73,
     "loc": 2,
     "doc": "A saved document whose meaning cannot be carried into the graph."
    },
    {
     "name": "carry_into_graph",
     "kind": "function",
     "line": 77,
     "loc": 86,
     "doc": "`document` with its crop and span moved into the pipeline."
    },
    {
     "name": "_refuse_a_detector",
     "kind": "function",
     "line": 165,
     "loc": 15,
     "doc": "Refuse a document whose detection cannot be carried \u2014 see the docstring."
    },
    {
     "name": "_refuse_taken",
     "kind": "function",
     "line": 182,
     "loc": 14,
     "doc": "Refuse rather than disambiguate a derived id the document already uses."
    },
    {
     "name": "_span_params",
     "kind": "function",
     "line": 198,
     "loc": 11,
     "doc": "The span node's parameters: the clip's bounds, or the identity range."
    },
    {
     "name": "_pinning",
     "kind": "function",
     "line": 211,
     "loc": 22,
     "doc": "`replicate` without its `roi`, pinning that box on every crop node."
    }
   ],
   "calls": [
    [
     "carry_into_graph",
     "_pinning"
    ],
    [
     "carry_into_graph",
     "_refuse_a_detector"
    ],
    [
     "carry_into_graph",
     "_refuse_taken"
    ],
    [
     "carry_into_graph",
     "_span_params"
    ],
    [
     "_refuse_a_detector",
     "UnupgradableDocumentError"
    ],
    [
     "_refuse_taken",
     "UnupgradableDocumentError"
    ],
    [
     "_pinning",
     "UnupgradableDocumentError"
    ]
   ],
   "uses": [
    [
     "carry_into_graph",
     "sieve.filters.crop",
     "CropParams"
    ],
    [
     "carry_into_graph",
     "sieve.filters.crop",
     "WHOLE_FRAME"
    ],
    [
     "carry_into_graph",
     "sieve.filters.span",
     "SpanParams"
    ],
    [
     "_span_params",
     "sieve.filters.span",
     "SpanParams"
    ],
    [
     "_pinning",
     "sieve.filters.crop",
     "CropParams"
    ],
    [
     "_pinning",
     "sieve.filters.crop",
     "WHOLE_FRAME"
    ]
   ]
  },
  "sieve.storage.__init__": {
   "package": "sieve.storage",
   "layerPackage": "sieve.storage",
   "band": 4,
   "loc": 10,
   "isInit": true,
   "ghost": false,
   "doc": "What SIEVE writes at rest, and nothing about what it means.",
   "annotation": "",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.storage.crop_writer": {
   "package": "sieve.storage",
   "layerPackage": "sieve.storage",
   "band": 4,
   "loc": 153,
   "isInit": false,
   "ghost": false,
   "doc": "FFV1 in Matroska, written frame by frame from arrays.",
   "annotation": "",
   "external": [
    "av",
    "collections",
    "fractions",
    "numpy",
    "pathlib",
    "typing"
   ],
   "symbols": [
    {
     "name": "CropWriteError",
     "kind": "class",
     "line": 53,
     "loc": 2,
     "doc": "The artifact could not be encoded: no frames, or a shape that changed."
    },
    {
     "name": "_VideoStream",
     "kind": "class",
     "line": 57,
     "loc": 19,
     "doc": "The encoding surface this module uses, named so strict typing can see it."
    },
    {
     "name": "_OutputContainer",
     "kind": "class",
     "line": 78,
     "loc": 6,
     "doc": "The muxing surface, for `_VideoStream`'s reason."
    },
    {
     "name": "write_ffv1",
     "kind": "function",
     "line": 86,
     "loc": 51,
     "doc": "Encode `frames` to `path` as FFV1 in Matroska. Returns the frame count."
    },
    {
     "name": "_source_format",
     "kind": "function",
     "line": 139,
     "loc": 14,
     "doc": "The PyAV format naming this array's own layout."
    }
   ],
   "calls": [
    [
     "write_ffv1",
     "CropWriteError"
    ],
    [
     "write_ffv1",
     "_OutputContainer"
    ],
    [
     "write_ffv1",
     "_VideoStream"
    ],
    [
     "write_ffv1",
     "_source_format"
    ],
    [
     "_source_format",
     "CropWriteError"
    ]
   ],
   "uses": []
  }
 },
 "ghosts": {
  "sieve.core.config": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "pydantic-settings app config \u2014 todo/application-config.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.core.constants": {
   "package": "sieve.core",
   "layerPackage": "sieve.core",
   "band": 6,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "hash seeds, cache format version (currently inline)",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.backend.namespace": {
   "package": "sieve.backend",
   "layerPackage": "sieve.backend",
   "band": 4,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "array-API namespace resolution \u2014 todo/gpu-execution.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.storage.zarr_store": {
   "package": "sieve.storage",
   "layerPackage": "sieve.storage",
   "band": 4,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "Zarr v3 arrays, the general store \u2014 todo/materialization.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.storage.sharding": {
   "package": "sieve.storage",
   "layerPackage": "sieve.storage",
   "band": 4,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "workload-specific sharding",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.workers.manager": {
   "package": "sieve.workers",
   "layerPackage": "sieve.workers",
   "band": 2,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "crash isolation \u2014 todo/process-isolation.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.workers.protocol": {
   "package": "sieve.workers",
   "layerPackage": "sieve.workers",
   "band": 2,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "versioned IPC",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.workers.shm_transport": {
   "package": "sieve.workers",
   "layerPackage": "sieve.workers",
   "band": 2,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "shared-memory frame transport",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.workers.process": {
   "package": "sieve.workers",
   "layerPackage": "sieve.workers",
   "band": 2,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "worker lifecycle, cooperative cancellation",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.observe.logging": {
   "package": "sieve.observe",
   "layerPackage": null,
   "band": null,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "structlog JSON Lines",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.observe.log_aggregator": {
   "package": "sieve.observe",
   "layerPackage": null,
   "band": null,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "per-worker stream merge",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.observe.results": {
   "package": "sieve.observe",
   "layerPackage": null,
   "band": null,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "Parquet results dataset",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.bench.profiling": {
   "package": "sieve.bench",
   "layerPackage": "sieve.bench",
   "band": 1,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "VizTracer + py-spy, both already in the dev group",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.hpc.handoff": {
   "package": "sieve.hpc",
   "layerPackage": null,
   "band": null,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "DAG -> job script \u2014 todo/hpc-handoff-and-review-mode.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.hpc.sweep": {
   "package": "sieve.hpc",
   "layerPackage": null,
   "band": null,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "parameter sweeps, immutable fragments",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.review.output": {
   "package": "sieve.review",
   "layerPackage": null,
   "band": null,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "VISION step 7 review contract \u2014 todo/hpc-handoff-and-review-mode.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.cli.hpc_cmd": {
   "package": "sieve.cli",
   "layerPackage": "sieve.cli",
   "band": 0,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "arrives with hpc/handoff.py",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  },
  "sieve.gui.state": {
   "package": "sieve.gui",
   "layerPackage": "sieve.gui",
   "band": 0,
   "loc": 0,
   "isInit": false,
   "ghost": true,
   "doc": "",
   "annotation": "only when UI state has no natural owner; see docs/SETTLED.md",
   "external": [],
   "symbols": [],
   "calls": [],
   "uses": []
  }
 },
 "edges": [
  {
   "src": "sieve.backend.dispatch",
   "dst": "sieve.core.filter_base",
   "names": [
    "FilterSpec",
    "Mode",
    "ParamsBase",
    "StreamKind"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.backend.dispatch",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "FrameSpan"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.backend.identity",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.bench.__init__",
   "dst": "sieve.bench.budgets",
   "names": [
    "BUDGETS",
    "Budget",
    "BudgetMissError",
    "Regime",
    "check"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.bench.metrics",
   "dst": "sieve.bench.budgets",
   "names": [
    "BUDGETS",
    "Budget"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.bench.retention_trace",
   "dst": "sieve.core.request_intent",
   "names": [
    "RequestKind"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.bench.sweep",
   "dst": "sieve.mutual.machine",
   "names": [
    "cpu_classes"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.__init__",
   "names": [
    "__version__"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.cli.detect_cmd",
   "names": [
    "detect_project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.cli.inspect_cmd",
   "names": [
    "inspect_filters"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.cli.materialize_cmd",
   "names": [
    "materialize_replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.cli.preview_cmd",
   "names": [
    "preview_project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.cli.run_cmd",
   "names": [
    "run_project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.cli.sweep_cmd",
   "names": [
    "sweep_decode"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.app",
   "dst": "sieve.decode.quiet",
   "names": [
    "silence_raw_format_warning"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.core.filter_registry",
   "names": [
    "FilterRegistry"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "Project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.decode.ffmpeg",
   "names": [
    "FfmpegLoweredFrameSource",
    "ffmpeg_decoder_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.decode.prefetch",
   "names": [
    "PrefetchFrameSource"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError",
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.pipeline.lowering",
   "names": [
    "lower_resolved_source"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.common",
   "dst": "sieve.pipeline.resolve_source",
   "names": [
    "ResolvedSource"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "NoKernelError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.cli.common",
   "names": [
    "WORKERS_OPTION",
    "frame_source",
    "load_project",
    "refuse",
    "span_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "ElementNames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.core.ops.wavelet",
   "names": [
    "ALL_CORES"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "DetectorSettings",
    "Project",
    "resolved_detector"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.detect.tables",
   "names": [
    "DetectionExport",
    "TableVerificationError",
    "write_tables"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.filters.detect",
   "names": [
    "DetectParams",
    "DetectorUpdate",
    "detect"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.pipeline.cache",
   "names": [
    "MemoryFrameStore"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag",
    "GraphError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.pipeline.executor",
   "names": [
    "FrameSource",
    "UnrunnableNodeError",
    "execute"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.pipeline.plan",
   "names": [
    "ExecutionPlan"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.pipeline.resolve_source",
   "names": [
    "resolve"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.detect_cmd",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.inspect_cmd",
   "dst": "sieve.backend.dispatch",
   "names": [
    "KERNELS"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.inspect_cmd",
   "dst": "sieve.core.filter_base",
   "names": [
    "FilterSpec",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.inspect_cmd",
   "dst": "sieve.core.filter_registry",
   "names": [
    "REGISTRY",
    "UnknownFilterError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.inspect_cmd",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover",
    "guidance_path"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.inspect_cmd",
   "dst": "sieve.pipeline.cache_key",
   "names": [
    "is_cacheable"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.cli.common",
   "names": [
    "load_project",
    "refuse",
    "span_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.pipeline.dag",
   "names": [
    "graph_needs_chroma"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.pipeline.materialize",
   "names": [
    "CropVerificationError",
    "MaterializeCancelledError",
    "materialize_crop"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.materialize_cmd",
   "dst": "sieve.storage.crop_writer",
   "names": [
    "CropWriteError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "NoKernelError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.bench.budgets",
   "names": [
    "BUDGETS"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.bench.metrics",
   "names": [
    "MetricBus",
    "Recorder"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.cli.common",
   "names": [
    "FrameSourceContext",
    "WORKERS_OPTION",
    "frame_source",
    "load_project",
    "lower_source_contract",
    "refuse",
    "span_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "Pipeline",
    "Project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.pipeline.cache",
   "names": [
    "MemoryFrameStore"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag",
    "GraphError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.pipeline.executor",
   "names": [
    "UnrunnableNodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.pipeline.preview",
   "names": [
    "PreviewRender",
    "PreviewSession"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.pipeline.resolve_source",
   "names": [
    "ResolvedSource",
    "resolve"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.preview_cmd",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "NoKernelError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.cli.common",
   "names": [
    "FrameSourceContext",
    "WORKERS_OPTION",
    "frame_source",
    "load_project",
    "lower_source_contract",
    "refuse",
    "span_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.pipeline.cache",
   "names": [
    "FrameStore",
    "MemoryFrameStore",
    "NullFrameStore"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag",
    "GraphError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.pipeline.executor",
   "names": [
    "FrameSource",
    "UnrunnableNodeError",
    "execute"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.pipeline.plan",
   "names": [
    "ExecutionPlan"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.pipeline.resolve_source",
   "names": [
    "ResolvedSource",
    "resolve"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.run_cmd",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.sweep_cmd",
   "dst": "sieve.bench.sweep",
   "names": [
    "AffinityUnavailableError",
    "Cell",
    "Reading",
    "class_core_sets",
    "curvature",
    "design",
    "sized_core_sets",
    "sweep"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.sweep_cmd",
   "dst": "sieve.cli.common",
   "names": [
    "frame_source",
    "refuse"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.cli.sweep_cmd",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.__init__",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CostEstimate",
    "FilterSpec",
    "Mode",
    "ParamsBase",
    "StreamKind",
    "StreamSpec",
    "TableSpec",
    "UNCHANGED_RATE",
    "source_warmup_frames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.__init__",
   "dst": "sieve.core.filter_registry",
   "names": [
    "DuplicateFilterError",
    "FilterRegistry",
    "REGISTRY",
    "UnknownFilterError",
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.__init__",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "DetectorSettings",
    "Edge",
    "Node",
    "PROJECT_SUFFIX",
    "Pipeline",
    "Project",
    "SCHEMA_VERSION",
    "Sink",
    "SourceRef",
    "as_project_path",
    "project_path_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.__init__",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate",
    "ReplicateSet"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.__init__",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameCount",
    "FrameIndex",
    "FrameRange",
    "FrameSpan",
    "MediaTime",
    "NO_FRAMES",
    "ROI",
    "VideoMetadata",
    "WORK_UNIT_ANCHOR",
    "WallTime",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.clip_window",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.clip_window",
   "dst": "sieve.core.types",
   "names": [
    "FrameCount",
    "MediaTime"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.filter_base",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "FrameCount",
    "NO_FRAMES",
    "WORK_UNIT_ANCHOR",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.filter_registry",
   "dst": "sieve.core.filter_base",
   "names": [
    "CaptionPart",
    "CostEstimate",
    "ElementDeclaration",
    "ElementNames",
    "FilterSpec",
    "Mode",
    "ParamsBase",
    "StreamSpec"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.history",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "PROJECT_SUFFIX",
    "Project"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.pipeline_model",
   "dst": "sieve.core.filter_base",
   "names": [
    "DEFAULT_PORT",
    "FILTER_ID_PATTERN",
    "PORT_PATTERN",
    "SEMVER_PATTERN"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.pipeline_model",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.pipeline_model",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.core.replicates",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.__init__",
   "dst": "sieve.decode.identity",
   "names": [
    "decoder_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.__init__",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError",
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.ffmpeg",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameCount",
    "FrameIndex",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.ffmpeg",
   "dst": "sieve.decode.lowered",
   "names": [
    "LOWERED_SOURCE_POLICY_VERSION",
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.ffmpeg",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError",
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.ffmpeg",
   "dst": "sieve.mutual.machine",
   "names": [
    "available_cpus"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.ffmpeg",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.ffmpeg",
   "dst": "sieve.mutual.shares",
   "names": [
    "PREVIEW_WORKERS"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.lowered",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.prefetch",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "FrameIndex",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.prefetch",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError",
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.prefetch",
   "dst": "sieve.mutual.machine",
   "names": [
    "available_cpus"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.prefetch",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.decode.reader",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameIndex",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.__init__",
   "dst": "sieve.detect.detector",
   "names": [
    "DetectorUpdate",
    "detect",
    "gate_to",
    "settled_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.detector",
   "dst": "sieve.core.ops.detection",
   "names": [
    "count_band_to_counts",
    "detect_gate",
    "gate_intervals",
    "inband_count",
    "settled_frames",
    "windowed_mean"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.detector",
   "dst": "sieve.core.ops.wavelet",
   "names": [
    "band_indices",
    "default_freqs",
    "morlet_band_power",
    "settled_frames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.detector",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "DetectorSettings"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.tables",
   "dst": "sieve.core.filter_base",
   "names": [
    "ElementNames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.tables",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "DetectorSettings"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.tables",
   "dst": "sieve.core.types",
   "names": [
    "FrameCount",
    "MediaTime"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.detect.tables",
   "dst": "sieve.detect.detector",
   "names": [
    "DetectorUpdate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.__init__",
   "dst": "sieve.core.filter_base",
   "names": [
    "FilterSpec"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.__init__",
   "dst": "sieve.core.filter_registry",
   "names": [
    "REGISTRY"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.background_ema",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "stateful_kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.background_ema",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.background_ema",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.background_ema",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "FrameCount",
    "FrameIndex",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.block_signal",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "stateful_kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.block_signal",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementKind",
    "ElementNames",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.block_signal",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.block_signal",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameCount",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.crop",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.crop",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.crop",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.crop",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "ROI",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "windowed_kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementKind",
    "ElementNames",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.core.ops.wavelet",
   "names": [
    "ALL_CORES",
    "PAD_EFOLDINGS",
    "band_indices",
    "coi_edge_samples",
    "default_freqs",
    "morlet_power"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "DetectorSettings"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameCount",
    "FrameIndex",
    "FrameSpan",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.detect",
   "dst": "sieve.detect.detector",
   "names": [
    "DetectorUpdate",
    "detect",
    "gate_to",
    "settled_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.downsample",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.downsample",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.downsample",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.downsample",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.motion_history",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "stateful_kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.motion_history",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.motion_history",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.motion_history",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameCount",
    "FrameIndex",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.normalize",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.normalize",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.normalize",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.normalize",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.rescale",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.rescale",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.rescale",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.rescale",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.span",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.span",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase",
    "UNBOUNDED_FRAME"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.span",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.span",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.temporal_baseline",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "stateful_kernel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.temporal_baseline",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "CaptionPart",
    "CostEstimate",
    "ElementRelation",
    "Mode",
    "ParamsBase"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.temporal_baseline",
   "dst": "sieve.core.filter_registry",
   "names": [
    "register_filter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.filters.temporal_baseline",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "FrameCount",
    "FrameIndex",
    "WorkUnits"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.__main__",
   "dst": "sieve.gui.app",
   "names": [
    "main"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.app",
   "dst": "sieve.__init__",
   "names": [
    "__version__"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.app",
   "dst": "sieve.decode.quiet",
   "names": [
    "silence_raw_format_warning"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.app",
   "dst": "sieve.gui.keyboard_handback",
   "names": [
    "KeyboardHandback"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.app",
   "dst": "sieve.gui.main_window",
   "names": [
    "MainWindow"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.app",
   "dst": "sieve.gui.wheel_steps",
   "names": [
    "WheelSteps"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.core.filter_base",
   "names": [
    "ElementNames",
    "caption_for_params"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.core.filter_registry",
   "names": [
    "REGISTRY",
    "UnknownFilterError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.core.ops.wavelet",
   "names": [
    "band_indices",
    "default_freqs"
   ],
   "status": "exception"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "DetectorSettings",
    "Edge",
    "Node",
    "Pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.filters.block_signal",
   "names": [
    "BlockSignalParams"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_model",
   "dst": "sieve.filters.detect",
   "names": [
    "DetectParams",
    "DetectorUpdate",
    "detect"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_stack",
   "dst": "sieve.gui.band_plot",
   "names": [
    "ACCENT",
    "DIM",
    "LINE",
    "PANEL",
    "TEXT",
    "plot_font"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_stack",
   "dst": "sieve.gui.chain_model",
   "names": [
    "ChainStep",
    "STAGE_CHIPS",
    "Stage",
    "Status",
    "StepGrade"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.chain_stack",
   "dst": "sieve.pipeline.crop_binding",
   "names": [
    "CropState"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.commands",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "DetectorSettings",
    "Node",
    "Pipeline",
    "edited_detector",
    "edited_params"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.commands",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.commands",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.commands",
   "dst": "sieve.gui.document",
   "names": [
    "DocumentState",
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.composite_view",
   "dst": "sieve.gui.band_plot",
   "names": [
    "ACCENT",
    "DIM",
    "PANEL",
    "TEXT",
    "argb_to_qimage",
    "plot_font",
    "ramp_lut"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.composite_view",
   "dst": "sieve.gui.zoom",
   "names": [
    "Magnifier"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.concurrency",
   "dst": "sieve.mutual.machine",
   "names": [
    "available_cpus"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.concurrency",
   "dst": "sieve.mutual.shares",
   "names": [
    "DETECTOR_WORKERS",
    "PLAYER_WORKERS",
    "PREVIEW_WORKERS",
    "WorkerSplit"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.count_plot",
   "dst": "sieve.core.filter_base",
   "names": [
    "ElementNames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.count_plot",
   "dst": "sieve.gui.band_plot",
   "names": [
    "BandPlot",
    "DETECT",
    "DIM",
    "plot_font"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.crop_tools",
   "dst": "sieve.core.types",
   "names": [
    "ROI",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.crop_tools",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.crop_tools",
   "dst": "sieve.gui.video_view",
   "names": [
    "CropMode"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.density_plot",
   "dst": "sieve.gui.band_plot",
   "names": [
    "ACCENT",
    "BandPlot",
    "argb_to_qimage",
    "ramp_lut"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.detector_worker",
   "dst": "sieve.filters.detect",
   "names": [
    "DetectParams",
    "DetectorUpdate",
    "detect"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.detector_worker",
   "dst": "sieve.gui.chain_model",
   "names": [
    "DetectorState"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.detector_worker",
   "dst": "sieve.gui.concurrency",
   "names": [
    "resolve_worker_split"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.detector_worker",
   "dst": "sieve.gui.density_plot",
   "names": [
    "DensitySurface",
    "density_surface"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.detector_worker",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.core.clip_window",
   "names": [
    "DEFAULT_WINDOW_SECONDS",
    "containing",
    "effective_window",
    "ended_at",
    "fitted",
    "moved_to"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact",
    "DetectorSettings",
    "Node",
    "Pipeline",
    "Project",
    "edited_detector",
    "edited_params",
    "equivalence_groups",
    "resolved_detector",
    "resolved_params"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate",
    "ReplicateSet"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.gui.commands",
   "names": [
    "AddReplicate",
    "EditDetector",
    "EditTuningParams",
    "RemoveReplicate",
    "RenameReplicate",
    "ResetTuning",
    "RestoreSnapshot",
    "SetClip",
    "SetReplicateROI",
    "SetReplicateROIs"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.pipeline.crop_binding",
   "names": [
    "CropBacking",
    "CropState",
    "backing_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.pipeline.dag",
   "names": [
    "graph_needs_chroma"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.document",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.executor_adapter",
   "dst": "sieve.bench.metrics",
   "names": [
    "METRICS",
    "MetricBus",
    "Sample"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.bench.metrics",
   "names": [
    "METRICS",
    "MetricBus"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.core.ops.wavelet",
   "names": [
    "default_freqs"
   ],
   "status": "exception"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "Node",
    "Pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.core.types",
   "names": [
    "WallTime"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.filters.block_signal",
   "names": [
    "BlockSignalParams",
    "Signal",
    "resolve_block"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.filters.detect",
   "names": [
    "gate_to"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.band_plot",
   "names": [
    "DIM"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.block_spin",
   "names": [
    "BlockSpinBox"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.chain_model",
   "names": [
    "BLOCK_SIGNAL_ELEMENT_NAMES",
    "ChainKind",
    "ChainStep",
    "DetectorState",
    "DetectorUpdate",
    "LiveChain",
    "Stage",
    "Status",
    "caption_for",
    "parity_chain",
    "recompute",
    "snapped_band_label"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.chain_stack",
   "names": [
    "ChainStackView"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.commit_combo",
   "names": [
    "CommitCombo"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.composite_view",
   "names": [
    "StepCompositeView"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.concurrency",
   "names": [
    "resolve_worker_split"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.count_plot",
   "names": [
    "CountPlot"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.density_plot",
   "names": [
    "DensityPlot",
    "DensitySurface"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.detector_worker",
   "names": [
    "DetectorFailure",
    "DetectorRequest",
    "DetectorResult",
    "DetectorRunner",
    "settled_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.graph_hud",
   "names": [
    "GraphHud"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.gray_toggle",
   "names": [
    "GrayToggle"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.materialize_worker",
   "names": [
    "MaterializeRunner"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.param_form",
   "names": [
    "param_rows"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.preferences",
   "names": [
    "Preferences"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.preview_runner",
   "names": [
    "PreviewRunner"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.rescale_cost",
   "names": [
    "RescaleCostHistory",
    "RescaleCostSample",
    "format_rescale_cost"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.scalogram_plot",
   "names": [
    "ScalogramPlot"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.source_boundary",
   "names": [
    "SourceBoundary"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.transport.player",
   "names": [
    "VideoPlayer"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.wizard",
   "names": [
    "StepWizard",
    "frame_to_qimage"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.wizard_lifecycle",
   "names": [
    "WizardAccepted",
    "WizardCancelled",
    "WizardLifecycle"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.gui.wizard_model",
   "names": [
    "catalog",
    "chain_from_pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.pipeline.preview",
   "names": [
    "PreviewRender"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.filter_tab",
   "dst": "sieve.pipeline.series_collector",
   "names": [
    "SeriesCollector"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.graph_hud",
   "dst": "sieve.bench.metrics",
   "names": [
    "Sample"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.graph_hud",
   "dst": "sieve.gui.band_plot",
   "names": [
    "ACCENT",
    "BAND",
    "BandPlot",
    "DIM",
    "plot_font"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.graph_hud",
   "dst": "sieve.gui.resource_probe",
   "names": [
    "ResourceSample"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.gray_toggle",
   "dst": "sieve.gui.preferences",
   "names": [
    "Preferences"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.history_dialog",
   "dst": "sieve.core.history",
   "names": [
    "Snapshot"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.core.history",
   "names": [
    "SnapshotStore",
    "history_directory"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "PROJECT_SUFFIX",
    "Project",
    "as_project_path",
    "project_path_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.core.types",
   "names": [
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.executor_adapter",
   "names": [
    "ExecutorAdapter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.filter_tab",
   "names": [
    "FilterTab"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.history_dialog",
   "names": [
    "HistoryDialog"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.preferences",
   "names": [
    "Preferences"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.preferences_dialog",
   "names": [
    "PreferencesDialog"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.preview_runner",
   "names": [
    "PreviewRunner"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.replicate_tab",
   "names": [
    "ReplicateTab"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.resource_probe",
   "names": [
    "MODE_IDLE",
    "MODE_PLAYBACK",
    "MODE_RENDER",
    "MODE_RENDER_FED_PLAYBACK",
    "ResourceProbe"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.timeline.bar",
   "names": [
    "TimelineBar"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.toast",
   "names": [
    "Toast"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.gui.transport.player",
   "names": [
    "VideoPlayer"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.pipeline.preview",
   "names": [
    "PreviewRender"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.main_window",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.materialize_worker",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.materialize_worker",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.materialize_worker",
   "dst": "sieve.pipeline.materialize",
   "names": [
    "MaterializeCancelledError",
    "materialize_crop"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.param_form",
   "dst": "sieve.core.filter_registry",
   "names": [
    "REGISTRY"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.param_form",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Node"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.param_form",
   "dst": "sieve.gui.band_plot",
   "names": [
    "DIM"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.param_form",
   "dst": "sieve.gui.commit_combo",
   "names": [
    "CommitCombo"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preferences",
   "dst": "sieve.core.clip_window",
   "names": [
    "DEFAULT_WINDOW_SECONDS"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preferences_dialog",
   "dst": "sieve.gui.preferences",
   "names": [
    "MAX_COARSE_INTERVAL_SECONDS",
    "MAX_PROXY_WIDTH",
    "MIN_COARSE_INTERVAL_SECONDS",
    "MIN_PROXY_WIDTH",
    "Preferences"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "KernelRegistry",
    "NoKernelError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.bench.metrics",
   "names": [
    "METRICS",
    "MetricBus"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.core.filter_registry",
   "names": [
    "FilterRegistry"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact",
    "Pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.core.types",
   "names": [
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.decode.ffmpeg",
   "names": [
    "FfmpegLoweredFrameSource",
    "ffmpeg_decoder_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.decode.prefetch",
   "names": [
    "PrefetchFrameSource"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError",
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.filters.__init__",
   "names": [
    "discover"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.gui.concurrency",
   "names": [
    "resolve_worker_split"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.gui.transport.render_ring",
   "names": [
    "RenderFrameRing"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.cache_key",
   "names": [
    "source_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag",
    "GraphError",
    "graph_needs_chroma"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.executor",
   "names": [
    "FrameResult",
    "UnrunnableNodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.lowering",
   "names": [
    "lower_resolved_source"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.preview",
   "names": [
    "Consumer",
    "PreviewRender",
    "PreviewSession"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.resolve_source",
   "names": [
    "ResolvedSource",
    "resolve"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.preview_runner",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.core.types",
   "names": [
    "ROI",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.gui.crop_tools",
   "names": [
    "CropToolsPanel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.gui.editing_sources",
   "names": [
    "EditingSources"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.gui.replicate_table",
   "names": [
    "Column",
    "EditingAwareDelegate",
    "ReplicateTableModel"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.gui.transport.player",
   "names": [
    "VideoPlayer"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_tab",
   "dst": "sieve.gui.video_view",
   "names": [
    "CropMode",
    "NO_SELECTION",
    "VideoView"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_table",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.replicate_table",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.rescale_cost",
   "dst": "sieve.core.types",
   "names": [
    "WallTime"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.resource_probe",
   "dst": "sieve.gui.concurrency",
   "names": [
    "resolve_worker_split"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.resource_probe",
   "dst": "sieve.mutual.machine",
   "names": [
    "MemoryUnreadableError",
    "process_memory_bytes"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.resource_probe",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.resource_probe",
   "dst": "sieve.mutual.shares",
   "names": [
    "WorkerSplit",
    "ledger_ceiling"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.scalogram_plot",
   "dst": "sieve.core.ops.wavelet",
   "names": [
    "coi_edge_samples"
   ],
   "status": "exception"
  },
  {
   "src": "sieve.gui.scalogram_plot",
   "dst": "sieve.gui.band_plot",
   "names": [
    "BandPlot",
    "DIM",
    "argb_to_qimage",
    "plot_font",
    "ramp_lut"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.source_boundary",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.source_boundary",
   "dst": "sieve.gui.chain_stack",
   "names": [
    "MATERIALIZE_PRICE",
    "SourceCard"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.source_boundary",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.source_boundary",
   "dst": "sieve.gui.materialize_worker",
   "names": [
    "MaterializeRequest",
    "MaterializeRunner"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.source_boundary",
   "dst": "sieve.pipeline.crop_binding",
   "names": [
    "CropBacking",
    "CropState",
    "evidence_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.timeline.bar",
   "dst": "sieve.core.clip_window",
   "names": [
    "ended_at_handle",
    "moved_to",
    "started_at"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.timeline.bar",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.timeline.bar",
   "dst": "sieve.core.types",
   "names": [
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.timeline.bar",
   "dst": "sieve.gui.document",
   "names": [
    "ReplicateDocument"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.timeline.bar",
   "dst": "sieve.gui.timeline.geometry",
   "names": [
    "Geometry"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.timeline.bar",
   "dst": "sieve.gui.transport.player",
   "names": [
    "VideoPlayer"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.coalescer",
   "dst": "sieve.core.request_intent",
   "names": [
    "RequestKind"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.decode_worker",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.decode_worker",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError",
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.decode_worker",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.pacing",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.bench.budgets",
   "names": [
    "BUDGETS"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.bench.metrics",
   "names": [
    "METRICS",
    "MetricBus"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.bench.retention_trace",
   "names": [
    "AccessEvent",
    "FROM_CACHE",
    "FROM_DECODE",
    "FROM_RING",
    "GET",
    "TRACE",
    "TraceRecorder"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.core.request_intent",
   "names": [
    "RequestKind"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.core.types",
   "names": [
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.preferences",
   "names": [
    "Preferences"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.transport.coalescer",
   "names": [
    "Request",
    "RequestCoalescer"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.transport.decode_worker",
   "names": [
    "DecodeWorker"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.transport.pacing",
   "names": [
    "feed_bounds",
    "playback_step"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.transport.proxy_cache",
   "names": [
    "ProxyFrameCache"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.transport.render_ring",
   "names": [
    "RenderFrameRing"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.gui.transport.scrub_policy",
   "names": [
    "ScrubPolicy"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.mutual.pool_meter",
   "names": [
    "PoolMeter"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.player",
   "dst": "sieve.mutual.shares",
   "names": [
    "PROXY_CACHE_SHARE",
    "resolved_bytes"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.render_ring",
   "dst": "sieve.bench.retention_trace",
   "names": [
    "AccessEvent",
    "PUT",
    "TRACE",
    "TraceRecorder",
    "UNKNOWN_PLAYHEAD"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.render_ring",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.render_ring",
   "dst": "sieve.gui.transport.decode_worker",
   "names": [
    "PROXY_WIDTH"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.render_ring",
   "dst": "sieve.gui.transport.proxy_cache",
   "names": [
    "ProxyFrameCache"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.transport.render_ring",
   "dst": "sieve.mutual.shares",
   "names": [
    "RENDER_RING_SHARE",
    "resolved_bytes"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.video_view",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.video_view",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.video_view",
   "dst": "sieve.gui.zoom",
   "names": [
    "MAX_ZOOM",
    "MIN_ZOOM",
    "Magnifier",
    "ZOOM_STEP"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard",
   "dst": "sieve.gui.band_plot",
   "names": [
    "DIM",
    "LINE",
    "PANEL",
    "TEXT",
    "plot_font"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard",
   "dst": "sieve.gui.chain_model",
   "names": [
    "BLOCK_SIGNAL_ELEMENT_NAMES",
    "ChainKind",
    "DetectorState",
    "DetectorUpdate",
    "LiveChain",
    "Status",
    "grade"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard",
   "dst": "sieve.gui.count_plot",
   "names": [
    "CountPlot"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard",
   "dst": "sieve.gui.density_plot",
   "names": [
    "DensityPlot",
    "DensitySurface"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard",
   "dst": "sieve.gui.param_form",
   "names": [
    "param_rows"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard",
   "dst": "sieve.gui.wizard_model",
   "names": [
    "Candidate",
    "CatalogEntry",
    "candidates_for_insert",
    "candidates_for_swap",
    "guidance_for",
    "insert_step",
    "swap_step"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_lifecycle",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_lifecycle",
   "dst": "sieve.gui.chain_model",
   "names": [
    "DetectorState",
    "DetectorUpdate",
    "LiveChain"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_lifecycle",
   "dst": "sieve.gui.density_plot",
   "names": [
    "DensitySurface"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_lifecycle",
   "dst": "sieve.gui.wizard",
   "names": [
    "StepWizard",
    "frame_to_qimage",
    "last_image_node_id"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_model",
   "dst": "sieve.core.filter_registry",
   "names": [
    "REGISTRY",
    "UnknownFilterError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_model",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Node",
    "Pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_model",
   "dst": "sieve.filters.__init__",
   "names": [
    "Guidance",
    "discover",
    "guidance_for"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_model",
   "dst": "sieve.gui.chain_model",
   "names": [
    "ChainKind",
    "ChainStep",
    "DetectorState",
    "LiveChain",
    "Stage",
    "Status",
    "grade"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.gui.wizard_model",
   "dst": "sieve.pipeline.dag",
   "names": [
    "linear_order"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.mutual.shares",
   "dst": "sieve.mutual.machine",
   "names": [
    "available_memory"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "FrameIndex"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.backend.identity",
   "names": [
    "backend_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.core.filter_base",
   "names": [
    "FilterSpec",
    "Mode"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Node",
    "resolved_params"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.decode.identity",
   "names": [
    "decoder_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.cache_key",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.crop_binding",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.crop_binding",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.crop_binding",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.crop_binding",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.core.filter_base",
   "names": [
    "ArraySpec",
    "ElementKind",
    "ElementNames",
    "FilterSpec",
    "SOURCE_ELEMENT_NAMES",
    "StreamSpec",
    "node_element",
    "node_element_names"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.core.filter_registry",
   "names": [
    "FilterRegistry",
    "REGISTRY",
    "UnknownFilterError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Node",
    "Pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.dag",
   "dst": "sieve.pipeline.cache_key",
   "names": [
    "NotCacheableError",
    "node_key",
    "source_key"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.executor",
   "dst": "sieve.backend.dispatch",
   "names": [
    "KERNELS",
    "Kernel",
    "KernelRegistry",
    "MergingKernel",
    "WindowedKernel",
    "unrunnable_reason"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.executor",
   "dst": "sieve.core.filter_base",
   "names": [
    "Mode",
    "node_warmup_frames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.executor",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Node"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.executor",
   "dst": "sieve.core.types",
   "names": [
    "ChannelSpec",
    "Frame",
    "FrameIndex",
    "FrameSpan",
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.executor",
   "dst": "sieve.pipeline.cache",
   "names": [
    "FrameStore",
    "NullFrameStore"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.executor",
   "dst": "sieve.pipeline.plan",
   "names": [
    "ExecutionPlan"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.core.filter_registry",
   "names": [
    "FilterRegistry"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "Node",
    "Pipeline",
    "resolved_params"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.core.types",
   "names": [
    "ROI",
    "VideoMetadata"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix",
    "LoweredScale",
    "LoweredStep",
    "roi_parts"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag",
    "GraphError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.lowering",
   "dst": "sieve.pipeline.resolve_source",
   "names": [
    "ResolvedSource"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact",
    "CropFormat"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.core.types",
   "names": [
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.decode.identity",
   "names": [
    "decoder_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoReader"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.pipeline.cache_key",
   "names": [
    "source_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.materialize",
   "dst": "sieve.storage.crop_writer",
   "names": [
    "write_ffv1"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.core.filter_base",
   "names": [
    "ALL_FRAMES",
    "ParamsBase",
    "input_warmup_frames"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "Node",
    "resolved_params"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.core.types",
   "names": [
    "FrameCount",
    "FrameIndex",
    "FrameRange",
    "NO_FRAMES",
    "ROI"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.plan",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.backend.dispatch",
   "names": [
    "Backend",
    "KernelRegistry"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.core.filter_registry",
   "names": [
    "FilterRegistry"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "Pipeline"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.core.types",
   "names": [
    "FrameIndex"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.pipeline.cache",
   "names": [
    "FrameStore",
    "MemoryFrameStore"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.pipeline.dag",
   "names": [
    "Dag"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.pipeline.executor",
   "names": [
    "FrameResult",
    "FrameSource",
    "execute"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.preview",
   "dst": "sieve.pipeline.plan",
   "names": [
    "ExecutionPlan"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.core.pipeline_model",
   "names": [
    "ClipRange",
    "CropArtifact"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.core.replicates",
   "names": [
    "Replicate"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.core.types",
   "names": [
    "Frame",
    "FrameIndex"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.decode.lowered",
   "names": [
    "LoweredPrefix"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.decode.reader",
   "names": [
    "VideoDecodeError"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.pipeline.cache_key",
   "names": [
    "source_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.pipeline.executor",
   "names": [
    "FrameSource"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.resolve_source",
   "dst": "sieve.pipeline.source_home",
   "names": [
    "SourceHome"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.series_collector",
   "dst": "sieve.pipeline.executor",
   "names": [
    "FrameResult"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.source_home",
   "dst": "sieve.pipeline.cache_key",
   "names": [
    "source_identity"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.upgrade",
   "dst": "sieve.filters.crop",
   "names": [
    "CropParams",
    "WHOLE_FRAME"
   ],
   "status": "ok"
  },
  {
   "src": "sieve.pipeline.upgrade",
   "dst": "sieve.filters.span",
   "names": [
    "SpanParams"
   ],
   "status": "ok"
  }
 ]
};
