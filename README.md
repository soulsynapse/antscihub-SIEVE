# antscihub-SIEVE

SIEVE is a tool to filter out behaviors from video without the need for training.

If there is a *pure signal* that can identify your behavior, SIEVE enables you to isolate that.

Signal Isolation for Ethological Video Events. This milestone provides the
Replicates workspace: portable video assets, editable crop layouts, recursive
child-replicate derivation, lineage navigation, and a PyQt6 desktop interface.

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

# In VS Code, open and run the top-level sieve_gui.py file.
.\.venv\Scripts\python.exe .\sieve_gui.py
```

The CLI does not import Qt and continues to work when the GUI extra is not
installed. FFmpeg and FFprobe must be available on `PATH`.

Video assets have no source/replicate type. Lineage records only what is known:
an asset may have a known parent, may have children, may have both, or may have
no recoverable parent information. Every asset can be cropped through the same
recursive workflow.
