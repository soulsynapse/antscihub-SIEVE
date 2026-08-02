"""Crop: the milestone tool (docs/archive/PLAN.md, Phase 3).

A Tool whose Params hold the drawn ROI regions, lowering to a Resample,
viewed as Image with the ROI overlay bound to the param field
(ARCHITECTURE.md "Tools"; DESIGN-SESSION.md Exchange 2). The Params
fields are undesigned surface -- nothing quotable beyond the contract on
sieve.tools.base.Tool -- so this marker is behavior-only.
"""

from sieve.debt import Owed

raise Owed(
    "crop tool: Params (ROI regions), lower -> Resample, view -> Image with"
    " ROI overlay; ARCHITECTURE.md 'Tools', DESIGN-SESSION.md Exchange 2"
)
