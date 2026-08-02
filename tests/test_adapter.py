"""Adapter behavior, proven in isolated pytest runs on disposable repos.

The live tree must stay at zero markers, so every scenario builds a fixture
repo carrying a byte-identical copy of the real tests/conftest.py at the
same relative location, exercising its root-relative logic unchanged.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER = (REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")


def make_repo(pytester, test_files: dict[str, str]) -> None:
    (pytester.path / "src" / "sieve").mkdir(parents=True)
    tests_dir = pytester.path / "tests"
    tests_dir.mkdir()
    (tests_dir / "conftest.py").write_text(ADAPTER, encoding="utf-8")
    for name, source in test_files.items():
        (tests_dir / name).write_text(source, encoding="utf-8")


def test_member_marker_in_test_function_skips(pytester):
    make_repo(
        pytester,
        {
            "test_x.py": (
                "from sieve.debt import Owed\n"
                "\n"
                "\n"
                "def test_roundtrip():\n"
                '    raise Owed("conformance: round-trip")\n'
            )
        },
    )
    result = pytester.runpytest_subprocess("tests", "-ra")
    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*owed: conformance: round-trip*"])


def test_module_form_test_file_skips(pytester):
    make_repo(
        pytester,
        {
            "test_conformance.py": (
                '"""Conformance suite placeholder."""\n'
                "from sieve.debt import Owed\n"
                "\n"
                'raise Owed("conformance suite: not built")\n'
            )
        },
    )
    result = pytester.runpytest_subprocess("tests", "-ra")
    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*owed: conformance suite: not built*"])


def test_unseen_marker_fails(pytester):
    make_repo(
        pytester,
        {
            "test_sneaky.py": (
                "from sieve.debt import Owed\n"
                "\n"
                "\n"
                "def test_sneaky():\n"
                "    exc = Owed\n"
                '    raise exc("sneaky")\n'
            )
        },
    )
    result = pytester.runpytest_subprocess("tests")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*cannot see*"])


def test_marker_reached_through_top_level_import_skips(pytester):
    make_repo(
        pytester,
        {
            "store_placeholder.py": (
                '"""Store placeholder."""\n'
                "from sieve.debt import Owed\n"
                "\n"
                'raise Owed("store: not built")\n'
            ),
            "test_store.py": (
                "import store_placeholder  # noqa: F401\n"
                "\n"
                "\n"
                "def test_store():\n"
                "    assert True\n"
            ),
        },
    )
    result = pytester.runpytest_subprocess("tests", "-ra")
    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*owed: store: not built*"])


def test_module_form_file_matching_the_other_default_glob_skips(pytester):
    make_repo(
        pytester,
        {
            "conformance_test.py": (
                '"""Conformance suite placeholder."""\n'
                "from sieve.debt import Owed\n"
                "\n"
                'raise Owed("conformance suite: not built")\n'
            )
        },
    )
    result = pytester.runpytest_subprocess("tests", "-ra")
    result.assert_outcomes(skipped=1)


def test_unseen_marker_at_collection_fails_with_naming(pytester):
    make_repo(
        pytester,
        {
            "test_sneaky_import.py": (
                "from sieve.debt import Owed\n"
                "\n"
                "exc = Owed\n"
                'raise exc("sneaky at import")\n'
            )
        },
    )
    result = pytester.runpytest_subprocess("tests")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*cannot see*"])


def test_teardown_marker_stays_red(pytester):
    make_repo(
        pytester,
        {
            "test_teardown.py": (
                "import pytest\n"
                "from sieve.debt import Owed\n"
                "\n"
                "\n"
                "@pytest.fixture\n"
                "def fx():\n"
                "    yield\n"
                "    exc = Owed\n"
                '    raise exc("cleanup reaches unbuilt code")\n'
                "\n"
                "\n"
                "def test_uses_fx(fx):\n"
                "    assert True\n"
            )
        },
    )
    result = pytester.runpytest_subprocess("tests")
    result.assert_outcomes(passed=1, errors=1)


def test_enumeration_failure_exits_pointedly(pytester):
    make_repo(pytester, {"test_ok.py": "def test_ok():\n    assert True\n"})
    bad = pytester.path / "src" / "sieve" / "broken.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    result = pytester.runpytest_subprocess("tests")
    assert result.ret == 4
    result.stderr.fnmatch_lines(["*debt enumeration failed*"])


def test_marker_reached_through_import_skips(pytester):
    make_repo(
        pytester,
        {
            "store_placeholder.py": (
                '"""Store placeholder."""\n'
                "from sieve.debt import Owed\n"
                "\n"
                'raise Owed("store: not built")\n'
            ),
            "test_store.py": (
                "def test_store():\n"
                "    import store_placeholder  # noqa: F401\n"
            ),
        },
    )
    result = pytester.runpytest_subprocess("tests", "-ra")
    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*owed: store: not built*"])
