# The plans as they stand

2026-11-17. The baseline `docs/spec/what-a-node-declares.md` compares every later deliverable
with: `docs/findings/experiments/2026-11-17-the-plans-as-they-stand.py video-tests <out>` writes
everything below the next line, so a later run's file is compared with this one whole.

The first part is `python -m sieve_player <document> --plan`'s own print, a document a block.
`--plan` hands `plan` no `cut_file`, so no node serves a file there. The second part is a Graph's
plan with no window, under the store as it stood: the video the document's selector picks, and
each path input's loader laid on its node as `window.py`'s `_pick_paths` lays it, done by the
one-off and not by the window. A served node's key there is its file's, and every key below it
differs from the first part's. Not here: `blobs-to-mask` and `crop` of `testing-crop.json`, tools
since retired, which the document does not resolve.

Printed at `41a6ea7c`.

## What `--plan` prints

### `video-tests/GoPro clip single v5.json`

```
video         video    de3c51a901468086                
reduce        series   1cd5861022a51ac6  head   step   
smooth        series   17ef4939a5f601b1  chain  whole  
changeenergy  frame    e802acbdbcda30a9  walked        
coarsegrain   frame    15c876374dfc0295                
csv           series   a52c9e12de05d6c6  chain  whole  
```

### `video-tests/GoPro clip single.json`

```
video         video    de3c51a901468086                
reduce        series   1cd5861022a51ac6  head   step   
smooth        series   17ef4939a5f601b1  chain  whole  
changeenergy  frame    e802acbdbcda30a9  walked        
coarsegrain   frame    15c876374dfc0295                
csv           series   a52c9e12de05d6c6  chain  whole  
```

### `video-tests/GoPro clip.json`

```
video         video    b617bf2f4c5c5647                
reduce        series   fa130b794d4c3d84  head   step   
smooth        series   9ff326d10991564f  chain  whole  
file          selector 711a69037c0dffb6                
changeenergy  frame    c83e6400a98c7a78  walked        
coarsegrain   frame    38775ce4165eaae6                
region        frame    b4b6b9d72fd228d7                
csv           series   f0c85eeba2da7fb3  chain  whole  
```

### `video-tests/bg-subtract-compare.json`

```
video        video    70c1bbf090ed6864                
bg-subtract  frame    fc6fb9ad0b946eb0                
background   frame    5f5ae8dd0246b8d5                
threshold    frame    0d54ae398f4de7d6                
blobs        frame    3e541d8a3446da0b  walked        
```

### `video-tests/purb-168-178.json`

```
video      video    39206ed636727c5f                
threshold  frame    6397a016059d12bb                
blobs      frame    d8bbfc588acfba89  walked        
travel     series   f870884c6e0600c7  chain  step   
track      series   308000a827efd1cf  head   step   
size       series   0f5432e9bb6ec977  head   step   
count      series   140890e131bfcc4b  head   step   
rescale    frame    0f8a4be2a918f4a4                
```

### `video-tests/purb-settings.json`

```
video      video    e5de46d659c2aadd                
track      series   8ae6e6ef60e8e186  head   step   
count      series   54f4f5075e88af4e  chain  step   
size       series   b6c257f218954c6d  chain  step   
travel     series   d1da4009c59056f9  chain  step   
region     frame    ea9ad2a4d22bc600                
file       selector adea51ad0ebc630b                
smooth     series   45de03c0ff5a3388  chain  whole  
top-hat    frame    8300619be101b2a5                
threshold  frame    a802619b12e0e695                
detect     frame    7849487c50f20b53  walked        
```

### `video-tests/test.json`

```
video        video    b834d8820d8f7eb9                
motion       frame    280e6e5d049dbe34  walked        
reduce       series   9116328c95059e92  head   step   
smooth       series   ca845b3135bfac48  chain  whole  
coarsegrain  frame    aa368e7659fd6684                
```

### `video-tests/testing-crop.json`

```
video          video    b834d8820d8f7eb9                
motion         frame    481459f945ad358d                in waits on crop
reduce         series   b1d15f21d29e7ff0  head   step   in waits on motion
smooth         series   22932259646b68fc                in waits on reduce
region         frame    de711bf9c16e375f                
blobs-to-mask  ?        5739e5baa9c7777e                
crop           ?        6f7bcd5536f97c68                
file           selector 0569b3f9082b2b5a                
```

### `video-tests/Thermal hysteresis 4 days/Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps.json`

```
video      video    107f5d06e3ff804a                
track      series   3ef8b26c267c9529  head   step   
travel     series   a0d70f7a8269673b  chain  step   
smooth     series   7d771ecd00df3e76  chain  whole  
csv        series   7189199cef17e53a  chain  whole  
size       series   0cdedea69f33c679  head   step   
region     frame    a786f8614a5e1166                
file       selector e6ea9a1cb6eb8347                
detect     frame    38e309c093aaa2f0  walked        
count      series   14047d1d7f4c73ae  head   step   
threshold  frame    cb9a1dc90a7766c0                
top-hat    frame    7999034069863210                
```

## The keys in the player, of each document a node of which serves a file

### `video-tests/GoPro clip.json`

| node | key | serves |
| --- | --- | --- |
| video | b617bf2f4c5c5647 |  |
| reduce | c878f1441ea94bf8 |  |
| smooth | 63f6f4aab0422a01 |  |
| file | 711a69037c0dffb6 |  |
| changeenergy | 8af2a5228f74b10d |  |
| coarsegrain | 108675440c0986eb |  |
| region | 84d81af8b10d0799 | square-6-b725e0bf7a6b4b38.mp4, print 64009a1933e916c0 |
| csv | 1da89084db37879e |  |

### `video-tests/purb-settings.json`

| node | key | serves |
| --- | --- | --- |
| video | e5de46d659c2aadd |  |
| track | f0841add87861f5d |  |
| count | b98ea56a515ac58a |  |
| size | 6f326013f18a315f |  |
| travel | 86bcc2c0fbb9eb12 |  |
| region | c069059020df0e19 | polygon-1-8802660265b19beb.mp4, print a332b36cf92db50b |
| file | adea51ad0ebc630b |  |
| smooth | c736b69c6adb5636 |  |
| top-hat | 4f65f1f7f2b69b43 |  |
| threshold | 5128ce6a15c46bda |  |
| detect | cf3bfd1c9ebe4c24 |  |

### `video-tests/Thermal hysteresis 4 days/Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps.json`

| node | key | serves |
| --- | --- | --- |
| video | 107f5d06e3ff804a |  |
| track | 9771d77bffd4e735 |  |
| travel | 6565be632e9fb00d |  |
| smooth | dad0935819fa8f1d |  |
| csv | 656b60696531212e |  |
| size | fd4eefce5726b502 |  |
| region | 6057145bdffdc6bf | square-8-7df4ba6b2b06e992.mp4, print 9a5a29339fcab613 |
| file | e6ea9a1cb6eb8347 |  |
| detect | acbc14c64985f97c |  |
| count | 24a6876bba6490c2 |  |
| threshold | e1d134a2f940fc99 |  |
| top-hat | 940e48657082c076 |  |

