# Detect

## When to use it

Use this when a graph needs the detector as an explicit node: Morlet band power
over a block-signal series, a value-band count, a D-frame mean, and a per-frame
gate channel. The output is a one-value float32 gray frame for each source
frame: `1` for detected, `0` for not detected, and `NaN` when the count
threshold is disarmed.

## What it does not do

It does not emit intervals or coordinates. Those are downstream derivations:
the current schema-v5 compatibility path still writes interval CSVs from
`DetectorUpdate`, and the first table-emitting filter belongs to the later sink
writer work. The registered kernel runs over the span it is handed; the GUI and
`sieve detect --csv` use this module's whole-series adapter so centered windows
and Morlet edge semantics do not move during the schema-v5 compatibility period.

## Cost

The expensive part is the Morlet transform over time and columns. Larger block
counts, lower frequency bands, and wider D windows all raise either memory,
history, or both. The node is windowed and is not cacheable under the current
per-frame cache contract.
