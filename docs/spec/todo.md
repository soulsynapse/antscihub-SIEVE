# Todo.md

This is kendrick's running list of todos.

- Figure out why track file is so big
- Tab menu filters, maximize, visual indicators, sorting..
- Make things that invalidate the cache loud so it doesn't surprise the user
- Add preferences window
- field inputs should be dropdowns, never manually entered
- A series tool whose result is set by a value inferred from the whole clip: walk the clip, fit
  two means to the signal, threshold by a rule (isodata, Otsu), and a `period` below cuts by
  that. Its kin, each a series tool on a gate with `period` cutting by it: runs padded, short
  ones dropped, those across a short gap joined, the longest kept, a bout criterion from every
  gap, two walks joined. What the back end is held to for it is in
  `docs/playground/JOURNAL.md`, "Standing words of his".

## Node displays

- Since nodes carry all their stuff, we can add visual toggles for stuff
  - Color coding?
  - in/out icons?
  - storage info?


## Maybe some day

- Auto arrange nodes by distance?