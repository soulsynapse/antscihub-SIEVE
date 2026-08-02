from sieve.debt import Owed


def test_owed_is_the_marker_exception():
    assert issubclass(Owed, Exception)
