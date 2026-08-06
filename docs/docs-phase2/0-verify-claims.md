The doc rests on claims from an earlier session that were never verified. Confirm or
refute each, with file paths and line references:

- [ ] Filter specs support multiple named input ports, and graph validation enforces that a
   node's incoming edges fill its declared ports exactly, and that each edge's emitted
   type is admitted by the port it feeds.



- [ ] The registry is decorator-discovery; nothing enumerates filters.



- [ ] Filter-ID string literals outside the filters/ directory appear in only a small number
   of GUI/lowering files, and in zero of: executor, graph validation, cache key
   computation, benchmarks.



- [ ] A generic params-form generator exists that builds a settings surface from a params
   model's fields and their constraints, and it is the path new filters actually take.



- [ ] The large hand-built filter UI module is a legacy island of a few parity steps, not the
   mechanism new filters go through.



- [ ] The GUI chain model is linear (an ordered list of steps), and a two-input filter cannot
   be represented in it at all.



- [ ] There is a second type vocabulary in the GUI, parallel to the core type system, whose
   remaining consumers are asking a narrow question that the core type system can now
   answer.


   
- [ ] Certain spatial operations are special-cased into the decoder as an optimization, and an
   unrecognized spatial filter still runs correctly, just slower.