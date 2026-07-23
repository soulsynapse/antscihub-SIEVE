# Processing ideas

## Benchmarkable channel input bases

Keep native-dimension FFmpeg-produced `rgb24` as the initial decoded evidence
contract, but do not require every future scientific channel to use RGB as its
only signal basis.

Many likely motion, change, texture, flow, and tensor channels may need only one
scalar intensity plane. When the supported benchmarking surfaces include
scientific processing, let the user compare at least:

```text
rgb24 decode -> explicit versioned luma transform -> channel

direct grayscale/luma decode -> channel
```

Potential benefits of a grayscale path include lower decoded bandwidth, about
one third of the pixel storage of `rgb24`, and less repeated preprocessing when
several channels consume the same scalar signal. It must not become an automatic
global optimization: color can contain biological evidence, and FFmpeg-produced
grayscale, encoded source luma, nonlinear RGB luma, and linear-light luminance
are not interchangeable representations.

### Future channel contract

When the first real channel establishes the channel API, allow a channel to
declare:

```text
accepted input basis ids
preferred input basis
required dtype, range, axes, and channel order
whether alternate bases are scientifically equivalent or merely supported
required preprocessing transform and version
```

A channel may accept multiple bases only when its behavior under each basis is
defined and tested. Input selection must be explicit in the captured request
and result provenance; it must not depend on whichever decoder path happens to
be fastest on one machine.

The orchestration layer should resolve one compatible working plane and share it
across compatible channels. Do not make each channel independently decode the
same window or independently calculate an unnamed grayscale conversion.

### Benchmark requirements

A future user-facing comparison should report separately:

- Decode and conversion throughput.
- Peak and retained memory.
- Working dimensions, frame span, batch size, and cache state.
- Source color metadata and the exact RGB/grayscale conversion.
- Channel runtime after input preparation.
- Numerical and detection-output differences between input bases.

Throughput alone is insufficient. A faster grayscale path is acceptable only
when the user has decided color is unnecessary for that analysis and the
comparison shows that the chosen basis preserves the required channel behavior.

Benchmark these candidate paths before adding direct grayscale delivery to the
working-window source. If direct grayscale is justified, extend the existing
explicit plane-id/descriptor seam narrowly; do not create a general plane
registry until multiple real consumers require one.
