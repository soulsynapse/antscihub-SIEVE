"""A folder's write and read rates and the time to open and read a small file, as a store would
see them. Run: python docs/playground/sim/diskrate.py <folder> [<folder> ...]. The read is of the
file just written, opened unbuffered by Windows so the page cache does not answer it.
"""
import os
import sys
import time

MB = 1 << 20
BIG, SMALL, MANY = 256 * MB, 4096, 200
FILE_FLAG_NO_BUFFERING = 0x20000000


def rates(folder):
    """(write MB/s through an fsync, read MB/s unbuffered, ms to write and to read one small file)."""
    block = os.urandom(8 * MB)
    big = os.path.join(folder, "diskrate.part")
    start = time.perf_counter()
    with open(big, "wb") as f:
        for _ in range(BIG // len(block)):
            f.write(block)
        f.flush()
        os.fsync(f.fileno())
    wrote = BIG / MB / (time.perf_counter() - start)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | (FILE_FLAG_NO_BUFFERING if os.name == "nt" else 0)
    fd = os.open(big, flags)
    start = time.perf_counter()
    while os.read(fd, 8 * MB):
        pass
    read = BIG / MB / (time.perf_counter() - start)
    os.close(fd)
    os.remove(big)
    names = [os.path.join(folder, f"diskrate-{i}.part") for i in range(MANY)]
    start = time.perf_counter()
    for name in names:
        with open(name + "~", "wb") as f:
            f.write(block[:SMALL])
        os.replace(name + "~", name)
    small_write = (time.perf_counter() - start) * 1000 / MANY
    start = time.perf_counter()
    for name in names:
        with open(name, "rb") as f:
            f.read()
    small_read = (time.perf_counter() - start) * 1000 / MANY
    for name in names:
        os.remove(name)
    return wrote, read, small_write, small_read


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        wrote, read, small_write, small_read = rates(folder)
        print(f"{folder}: write {wrote:.0f} MB/s, read {read:.0f} MB/s, "
              f"a small file {small_write:.2f} ms to write and rename, {small_read:.2f} ms to read")
