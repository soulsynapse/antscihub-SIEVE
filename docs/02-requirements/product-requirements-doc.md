# Product requirements document

This is what the product should do.

1. It needs to be performant, or if the user's machine is not strong enough, able to handle that.

## Filter contract
Everything is built around the filter contract. GUI widgets, CLI flags, JSON schema, guidance display, cost estimation all read from Filter.params_schema and Filter.guidance_md. No parallel definitions. 

## Purpose of the GUI
The GUI exists to produce a serializable artifact: the pipeline. Without this, SIEVE is going to have to undergo another rewrite. The pipeline, which is a DAG of filter invocations with params, is inherently a data structure that fully describes the run.

The GUI produces the pipeline. The CLI consumes it. **It is a central architectural commitment.**