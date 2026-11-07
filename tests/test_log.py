"""The stderr log: what is printed reaches the file and the stream it had, the previous log is kept, and the env var places or disables it."""
import io
import sys

from sieve_player.dev import console


def test_stderr_is_teed_into_the_log_and_the_last_log_kept(tmp_path, monkeypatch):
    kept = io.StringIO()
    monkeypatch.setattr(sys, "stderr", kept)
    path = tmp_path / "logs" / "stderr.log"
    log = console.log_stderr(str(path))
    print("first", file=sys.stderr)
    log.close()
    assert path.read_text(encoding="utf-8") == "first\n" and kept.getvalue() == "first\n"
    monkeypatch.setattr(sys, "stderr", kept)
    console.log_stderr(str(path)).close()
    assert (tmp_path / "logs" / "stderr.prev.log").read_text(encoding="utf-8") == "first\n" and path.read_text() == ""
    monkeypatch.setenv(console.LOG_ENV, "0")
    assert console.log_path() is None
    monkeypatch.setenv(console.LOG_ENV, "here.log")
    assert console.log_path() == "here.log"
    assert console.log_stderr(str(tmp_path / "logs" / "stderr.log" / "under-a-file")) is None   # a path that will not open: no log, stderr as it was


def test_a_stream_that_will_not_take_a_write_is_passed_over(tmp_path):
    kept, gone = io.StringIO(), open(tmp_path / "gone.log", "w")
    gone.close()
    tee = console._Tee(kept, gone)
    print("still", file=tee)                        # a full disk or a closed log never makes a traceback raise
    assert kept.getvalue() == "still\n"
