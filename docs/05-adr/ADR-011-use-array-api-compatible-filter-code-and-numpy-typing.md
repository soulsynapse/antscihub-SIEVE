# ADR-011: Use Array API-compatible filter code and NumPy typing

Reference: https://docs.arc42.org/section-9/

## Context

[INTENT] SIEVE's filter contract needs a backend registry, and the backend-dispatch
architecture anticipates NumPy CPU, CuPy GPU, and PyTorch GPU implementations.
[INTENT] Independently rewriting each filter against `numpy`, `cupy`, and
`torch`, the registry becomes a catalog of duplicated algorithms rather than a
dispatch mechanism.

[STABLE] The Python Array API standard defines a common array vocabulary across array
libraries. `array-api-compat` provides a compatibility layer for supported
NumPy, CuPy, and PyTorch arrays, including a way to obtain the array namespace
appropriate to an input. Writing portable numerical kernels against that
namespace creates a leverage point where one implementation can serve several
registered backends.

[INTENT] Some SIEVE operations sit outside the common API. Video decode, OpenCV operations,
shared-memory NumPy views, library-specific algorithms, device-specific
optimization, and some advanced indexing or signal-processing operations may
require a concrete library.

[INTENT] Array typing is a related but separate concern. SIEVE needs useful dtype
annotations and shape documentation without adopting an inactive shape-typing
package or claiming that Python's type system proves runtime array shapes.
`numpy.typing.NDArray` is maintained with NumPy and accurately describes
NumPy-specific arrays, but it does not describe CuPy arrays or PyTorch tensors.
jaxtyping can express dtype and symbolic shape annotations for array types
beyond JAX where that precision is valuable.

## Decision

Write filter numerical kernels against the Python Array API through
`array-api-compat` where the operations required by the algorithm are
available and have suitable semantics.

Obtain the array namespace from the actual input arrays or from a
backend-provided compatibility adapter. Use namespace operations rather than
hard-coded `numpy`, `cupy`, or `torch` calls inside portable kernels. Do not
coerce an input through `numpy.asarray` or otherwise transfer it to host memory
merely to make a portable kernel run.

One portable implementation may be registered for multiple backends when its
contract, numerical semantics, dtype behavior, determinism declaration, and
cost model are valid for each backend. Backend registration remains explicit;
Array API compatibility does not imply that every supported backend is
automatically correct or performant for every filter.

Keep backend-specific branches explicit and localized. Use them when:

- video decoding or OpenCV requires a NumPy host array;
- an operation is absent from or too constrained by the common Array API;
- a library-native implementation is materially faster or more numerically
  appropriate;
- device transfer, memory layout, synchronization, or stream ownership must
  be controlled; or
- backend determinism differs.

Do not scatter `if numpy`, `if cupy`, and `if torch` checks through the
algorithm. Put an unavoidable specialization behind a named backend adapter or
a small, documented dispatch boundary. A fallback that transfers data between
host and device must be explicit, included in the cost model, visible in
benchmarking, and covered by the cache/backend identity contract.

Use `numpy.typing.NDArray` for NumPy-specific boundaries and implementations,
including decode, OpenCV adapters, shared-memory views, and explicitly
NumPy-only filters. Include dtype parameters where they improve correctness,
for example:

```python
import numpy as np
import numpy.typing as npt

RgbFrame = npt.NDArray[np.uint8]
FloatPlane = npt.NDArray[np.float32]
```

Do not annotate a backend-neutral filter parameter as `NDArray` when it also
accepts CuPy arrays or PyTorch tensors. Define a project-level typing protocol
or alias for supported Array API-compatible objects and keep it separate from
the concrete NumPy aliases.

Document array dimensions with stable semantic names such as
`height width channel`, `time height width`, or `batch time feature`. Use
docstrings for ordinary public contracts. Adopt jaxtyping selectively where
symbolic shape and dtype annotations materially improve a complex filter,
adapter, or test. Parameterize jaxtyping annotations with the actual supported
array base types; do not assume its name restricts it to JAX.

Shape annotations are documentation and static-analysis aids unless a
deliberate runtime checker is configured. Do not add runtime shape-validation
wrappers to per-frame hot paths by default. The filter contract and tests
remain authoritative for runtime shape, dtype, range, and backend behavior.

Do not adopt nptyping. Its maintenance state and separate annotation model do
not justify another array-typing dependency when NumPy supplies
`numpy.typing.NDArray` and optional jaxtyping covers the shape-annotation cases
SIEVE may need.

Test each shared portable kernel against every backend it registers. Reuse the
property-based filter-contract suite from ADR-008 and compare backends with
explicit exact or tolerance-based expectations appropriate to the operation.
Tests must detect unintended host transfers, unsupported dtype promotion,
device changes, and backend-specific determinism differences.

## Alternatives considered

### Backend-specific NumPy, CuPy, and PyTorch implementations

[INTENT] This alternative permits maximal backend-specific optimization but duplicates
ordinary array algorithms and makes semantic drift likely. Distinct
implementations remain appropriate for operations outside the
common API, not as the default structure.

### NumPy source with automatic substitution

[INTENT] Aliasing `numpy` to another module or mechanically replacing `np` calls hides
semantic differences and does not reliably control device transfer, dtype
promotion, indexing, or unsupported operations. The Array API namespace makes
the portable subset explicit.

### NumPy only until GPU backends are implemented

[INTENT] Deferring portability makes early filter implementations establish NumPy-only
idioms and types that later need invasive rewrites. The repository is early
enough to keep portable kernels within the common subset from their first
implementation.

### nptyping

[INTENT] nptyping combines dtype and shape notation, but introduces a separate typing
model and an unsuitable maintenance dependency. It also does not solve runtime
portability across NumPy, CuPy, and PyTorch. NumPy's maintained typing module
and optional jaxtyping are preferred.

### jaxtyping everywhere

[INTENT] Uniform symbolic shape annotations could make dimensions highly visible, but
would add annotation complexity and potentially encourage runtime checking in
hot paths. SIEVE uses it selectively where shape relationships are difficult
to communicate accurately through types and docstrings alone.

### A SIEVE-specific array abstraction

[INTENT] A custom wrapper could normalize the supported backends and enforce SIEVE-specific
semantics, but would create another array library, complicate interoperability,
and obscure access to native operations. A thin compatibility and adapter
boundary is sufficient.

## Status

Accepted.

## Consequences

- Many filter kernels can serve NumPy, CuPy, and PyTorch registrations without
  copying the algorithm.
- The backend registry primarily describes capability, semantics, cost, and
  specialization rather than routine source duplication.
- Filter authors accept the minor stylistic cost of namespace-based operations
  and the constraints of the common Array API.
- Unsupported or performance-critical operations have visible,
  backend-specific escape hatches.
- NumPy-only boundaries receive precise `numpy.typing.NDArray` dtype aliases
  without contaminating backend-neutral interfaces.
- Shape semantics remain visible through docstrings and selective jaxtyping
  annotations.
- `array-api-compat` becomes a constrained runtime dependency; jaxtyping is an
  optional typing/development dependency unless production runtime checking is
  separately adopted.
- Cross-backend contract and numerical-equivalence tests are required for each
  shared implementation.
- Backend differences in promotion, precision, determinism, synchronization,
  and performance remain explicit responsibilities; common syntax does not
  guarantee common results.
- Host/device transfers must be deliberate and measurable rather than hidden
  inside compatibility code.

## References

- [Python Array API standard](https://data-apis.org/array-api/latest/)
- [array-api-compat](https://data-apis.org/array-api-compat/)
- [NumPy typing documentation](https://numpy.org/doc/stable/reference/typing.html)
- [jaxtyping documentation](https://docs.kidger.site/jaxtyping/)
- [SIEVE architecture: filter contract criteria](../04-architecture/ARCHITECTURE.md#6-filter-contract--criteria)
- [SIEVE architecture: backend dispatch criteria](../04-architecture/ARCHITECTURE.md#9-backend-dispatch--criteria)
- [ADR-008: Use pytest, Hypothesis, and pytest-benchmark](ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
