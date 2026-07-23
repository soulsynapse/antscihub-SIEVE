# SIEVE *(Signal Isolation for Ethological Video Events)*

SIEVE is a tool to filter out behaviors from video without the need for training, with a focus on efficiency.

The primary use categories:

1. Study feasibility assessments
2. HPC-assisted analysis
3. Feature vector composition
4. Temporal sampling 

## Development setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[gui,test]"
.\.venv\Scripts\sieve.exe --help
```

## Quick start

```powershell
# Register a video asset and add a draft crop. Assets are lineage-agnostic;
# roots and children are determined from recorded provenance.
sieve asset init .\video.mp4 --label "colony 07" --json
sieve layout add .\video.mp4 --box 20,40,500,600 --label rep1 --json

# Preview the exact plan, then create lossless portable child packages.
sieve derive .\video.mp4 --layout .\video.replicate-layout.json `
  --out .\replicates --profile lossless --plan --json
sieve derive .\video.mp4 --layout .\video.replicate-layout.json `
  --out .\replicates --profile lossless --json

# Or use the Replicates desktop workspace.
sieve-gui

# In Isolate, choose a time window and working grid, select normalization
# (Off or Per-frame z-score), then explicitly compute the post-decoder RGB601
# intensity channel. Changing normalization after a result exists safely
# recomputes the current window.

# In VS Code, open and run the top-level sieve_gui.py file.
.\.venv\Scripts\python.exe .\sieve_gui.py
```

## Media performance estimate

Measure the display representation used by Isolate and report whether the
media-service sequential path fits the asset's native frame budget:

```powershell
sieve media benchmark .\video.mp4
sieve media benchmark .\video.mp4 --json
```

Use `--native` to measure full-resolution RGB instead. This is more expensive
and answers a different question from ordinary viewer responsiveness:

```powershell
sieve media benchmark .\video.mp4 --native
```

Benchmarks run only when explicitly requested. Results describe the current
computer, backend, representation, and cache conditions; they are estimates,
not portable performance guarantees. The CLI estimate excludes GUI painting,
overlays, and scientific processing.

The CLI does not import Qt and continues to work when the GUI extra is not
installed. FFmpeg and FFprobe must be available on `PATH`.

Video assets have no source/replicate type. Lineage records only what is known:
an asset may have a known parent, may have children, may have both, or may have
no recoverable parent information. Every asset can be cropped through the same
recursive workflow.
