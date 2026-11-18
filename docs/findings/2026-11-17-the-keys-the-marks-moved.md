# The keys the marks moved

2026-11-17, the tree at `e9d86a31` and the same tree with `outline` of `blobs`, `filter` and
`track` and `csv`'s `beside footage` declared `"changes result": False`, the last deliverable of
`docs/spec/what-a-node-declares.md`. The baseline's one-off,
`docs/findings/experiments/2026-11-17-the-plans-as-they-stand.py video-tests <out>`, was run on
each, and `docs/findings/experiments/2026-11-17-the-keys-the-marks-moved.py <before> <after>`
prints the tables below of the two files. The run before the marks was equal to
`docs/findings/2026-11-17-the-plans-as-they-stand.md` below its Printed at line, so that finding
holds the keys before, whole.

Every key that differs is that of a node of one of the four tools or of a node below one. A held
run under a key before is found by nothing and walked again, and a csv on disk whose key line
holds one reads as stale on its card, no row of it differing.

## An outline changed on a track node

`docs/findings/experiments/2026-11-17-an-outline-changed-on-a-track-node.py`, a player offscreen
over a six-row clip made there, gray, threshold, blobs and track:

```
opened: track's key 10cd41fa08586e7c, blobs ran 6, track ran or stepped 7, track's draw handed 'box'; outline handed to blobs' computing False, to track's False
outline changed to contour: track's key 10cd41fa08586e7c, blobs ran 6, track ran or stepped 7, track's draw handed 'contour'; outline handed to blobs' computing False, to track's False
max_step changed to 9: track's key 4111c9209175a202, blobs ran 6, track ran or stepped 13, track's draw handed 'contour'; outline handed to blobs' computing False, to track's False
```

A wrong mark, `attach`'s `outline`, which its `run` reads, declared so in memory:
`tests/test_seams.py`'s seam is red with `KeyError: 'outline'`.

Not run: the player on the screen. Not measured: how long the documents' held runs take to walk
again.

## The keys

`--plan`, `video-tests/GoPro clip single v5.json`

| node | key before | key now |
| --- | --- | --- |
| csv | a52c9e12de05d6c6 | 263befcc5170f5bb |

`--plan`, `video-tests/GoPro clip single.json`

| node | key before | key now |
| --- | --- | --- |
| csv | a52c9e12de05d6c6 | 263befcc5170f5bb |

`--plan`, `video-tests/GoPro clip.json`

| node | key before | key now |
| --- | --- | --- |
| csv | f0c85eeba2da7fb3 | 6be9227346ddcccc |

`--plan`, `video-tests/bg-subtract-compare.json`

| node | key before | key now |
| --- | --- | --- |
| blobs | 3e541d8a3446da0b | f5160d91330e7753 |

`--plan`, `video-tests/purb-168-178.json`

| node | key before | key now |
| --- | --- | --- |
| blobs | d8bbfc588acfba89 | 3d15117b4a5acf08 |
| travel | f870884c6e0600c7 | c338cbe76423296e |
| track | 308000a827efd1cf | 5cc4a93ccf7c1a5e |
| size | 0f5432e9bb6ec977 | fb2d5148352f58ab |
| count | 140890e131bfcc4b | 2f7228e693aef143 |

`--plan`, `video-tests/purb-settings.json`

| node | key before | key now |
| --- | --- | --- |
| track | 8ae6e6ef60e8e186 | 71c7235a77cb656f |
| count | 54f4f5075e88af4e | 1ceebbf65f5eb163 |
| size | b6c257f218954c6d | 4ba7944693f34a7e |
| travel | d1da4009c59056f9 | 0c64c0e10b0f3755 |
| smooth | 45de03c0ff5a3388 | 6e0fc8609fd469b4 |

`--plan`, `video-tests/Thermal hysteresis 4 days/Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps.json`

| node | key before | key now |
| --- | --- | --- |
| track | 3ef8b26c267c9529 | 09c56776cdc9958e |
| travel | a0d70f7a8269673b | f9c2267ed3f155bc |
| smooth | 7d771ecd00df3e76 | 08f3da860f3cd567 |
| csv | 7189199cef17e53a | df7bdfb581d4968b |

in the player, `video-tests/GoPro clip.json`

| node | key before | key now |
| --- | --- | --- |
| csv | 1da89084db37879e | 97c0b5c0ce1a23ee |

in the player, `video-tests/purb-settings.json`

| node | key before | key now |
| --- | --- | --- |
| track | f0841add87861f5d | e225660c17b720a4 |
| count | b98ea56a515ac58a | 3d278f1b01390128 |
| size | 6f326013f18a315f | 86304418c2d15056 |
| travel | 86bcc2c0fbb9eb12 | 0ab486a9340f107c |
| smooth | c736b69c6adb5636 | 4c83fd5d4e3162d2 |

in the player, `video-tests/Thermal hysteresis 4 days/Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps.json`

| node | key before | key now |
| --- | --- | --- |
| track | 9771d77bffd4e735 | 21b1a34e05239efe |
| travel | 6565be632e9fb00d | a320d23387d62c8e |
| smooth | dad0935819fa8f1d | b95cc9f2521de74d |
| csv | 656b60696531212e | 1e4c6e54b40aa6df |

28 of 98 keys differ
