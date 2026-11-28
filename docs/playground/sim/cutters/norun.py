"""Frame tool of the miniature alone: `pad` with no `run`, a cutting tool that says nothing of
what it hands down, for docs/playground/sim/miniature.py to ask what the player makes of one.
"""
from pad import PARAMS, cut_extents, key_params, reach_in_rows  # noqa: F401

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "norun", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
CUT_BY = {"gate": ("signal", "tracks")}
