"""One-off: what the ledger takes to fold a store's discard as the discards it remembers pass its
limit. 700000 "evict" events of distinct rows are emitted to a Ledger through an Emitter and folded
a thousand at a time; said are the us an event of each 50th thousand, the mean and the worst
thousand, before the ledger remembers its limit of them and after. Run from the repo root:
python docs/findings/experiments/2026-11-15-what-a-discard-costs-the-ledger.py"""
import os
import sys
import time

sys.path.insert(0, os.getcwd())
from sieve_player.ledger import Ledger
from sieve_player.stream import EVICT, Emitter

stream, ledger = Emitter(), Ledger()
stream.on_event = ledger.event
limit, us = ledger._discards, []
for block in range(700):
    for i in range(1000):
        stream.emit(EVICT, None, block * 1000 + i, "a key", 64)
    t = time.perf_counter()
    ledger.view()
    us.append((time.perf_counter() - t) * 1000)
before, after = us[:limit // 1000], us[limit // 1000 + 1:]
print(f"the ledger remembers {limit} discards")
print("us an event, each 50th thousand:", " ".join(f"{us[i]:.1f}" for i in range(0, 700, 50)))
print(f"before the limit: mean {sum(before) / len(before):.1f}, worst thousand {max(before):.1f}")
print(f"past it:          mean {sum(after) / len(after):.1f}, worst thousand {max(after):.1f}")
