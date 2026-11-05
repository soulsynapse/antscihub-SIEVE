"""The stderr log: what is printed reaches the file and the stream it had, the previous log is kept, and the env var places or disables it."""
import io
import sys

import sieve_player


def test_stderr_is_teed_into_the_log_and_the_last_log_kept(tmp_path, monkeypatch):
    kept = io.StringIO()
    monkeypatch.setattr(sys, "stderr", kept)
    path = tmp_path / "logs" / "stderr.log"
    log = sieve_player.log_stderr(str(path))
    print("first", file=sys.stderr)
    log.close()
    assert path.read_text(encoding="utf-8") == "first\n" and kept.getvalue() == "first\n"
    monkeypatch.setattr(sys, "stderr", kept)
    sieve_player.log_stderr(str(path)).close()
    assert (tmp_path / "logs" / "stderr.prev.log").read_text(encoding="utf-8") == "first\n" and path.read_text() == ""
    monkeypatch.setenv(sieve_player.LOG_ENV, "0")
    assert sieve_player.log_path() is None
    monkeypatch.setenv(sieve_player.LOG_ENV, "here.log")
    assert sieve_player.log_path() == "here.log"
    assert sieve_player.log_stderr(str(tmp_path / "logs" / "stderr.log" / "under-a-file")) is None   # a path that will not open: no log, stderr as it was
