# What this helps with

This is just a list of potential things to think about for what constitutes a big stage of the filter architecture implementation.



1. **How the repo currently prevents the goal**, with concrete evidence from the actual
   code. Name the real file, the real duplicated vocabulary, the real second list.
2. **The failure mechanism**, i.e. *how* the violation produces divergence,
   contention, or breakage — the causal story, not an assertion that it's bad.
3. **Why it doesn't stay a fixed cost.** Both reference sections turn on scale:
   an incomplete contract is re-answered per filter; one shared file is a hundred
   changes funneled through one edit point. Every requirement needs its version of
   this, or it isn't a structural blocker — it's just cleanup, and belongs
   elsewhere.
4. **Dependency position.** What must hold before this can be done, and what
   specifically breaks if the order is reversed. A dependency claim with no
   failure attached to reordering is decoration; drop it or justify it.
5. **The done condition**, expressed as an observable property or as a test that
   would fail today and pass afterward. Not "the registry is refactored" but
   "registering a filter and nothing else makes it appear in the GUI."
6. **What is deliberately left open.** Name the decisions you are handing to the
   implementer — mechanism, data structure, whether something is generated or
   derived or checked, where the boundary sits. Making the latitude explicit is
   what stops an implementer from reverse-engineering a design they think you
   wanted.

# The prescription boundary

To make sure you don't necessarily overspecify. They cut in opposite directions and you need
both.

- **Over-specification test:** could two competent implementers arrive at
  materially different designs that each fully satisfy this section? If no, you
  have specified a solution. Remove the mechanism and keep the property it was
  protecting.
- **Under-specification test:** could an implementer satisfy every sentence you
  wrote and leave the original failure mode fully intact? If yes, the section is
  mush. Add the observable done condition, not more instructions.

# Evidence versus prescription

Current-state facts are evidence and must be concrete and specific. Future-state
statements must be properties. Do not let a filename that appears as evidence of
today's problem reappear as an implicit instruction about tomorrow's structure.
