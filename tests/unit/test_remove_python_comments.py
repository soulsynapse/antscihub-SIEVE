from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "remove_python_comments.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("remove_python_comments", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_removes_full_line_and_inline_comments() -> None:
    module = _load_script()
    source = "# first\nvalue = 1  # second\n    # third\n"

    updated, count = module.remove_comments(source)

    assert count == 3
    assert updated == "\nvalue = 1\n\n"
    compile(updated, "<test>", "exec")


def test_preserves_hashes_in_strings_and_docstrings() -> None:
    module = _load_script()
    source = '"""# docstring"""\nurl = "https://example.test/#part"\n'

    updated, count = module.remove_comments(source)

    assert count == 0
    assert updated == source


def test_preserves_newline_style() -> None:
    module = _load_script()
    source = "value = 1  # comment\r\nnext_value = 2\r\n"

    updated, count = module.remove_comments(source)

    assert count == 1
    assert updated == "value = 1\r\nnext_value = 2\r\n"


def test_write_mode_rewrites_a_requested_file(tmp_path: Path) -> None:
    module = _load_script()
    target = tmp_path / "sample.py"
    target.write_text('value = "# stays"  # goes\n', encoding="utf-8")

    exit_code = module.main(["--write", str(target)])

    assert exit_code == 0
    assert target.read_text(encoding="utf-8") == 'value = "# stays"\n'


def test_removes_docstrings_without_removing_other_strings() -> None:
    module = _load_script()
    source = (
        '"""module documentation"""\n'
        'value = "ordinary string"\n'
        "def function() -> None:\n"
        '    """function documentation"""\n'
        "    return None\n"
    )

    updated, count = module.remove_docstrings(source)

    assert count == 2
    assert "documentation" not in updated
    assert '"ordinary string"' in updated
    compile(updated, "<test>", "exec")


def test_replaces_an_only_docstring_with_pass() -> None:
    module = _load_script()
    source = 'class Empty:\n    """documentation"""\n'

    updated, count = module.remove_docstrings(source)

    assert count == 1
    assert updated == "class Empty:\n    pass\n"
    compile(updated, "<test>", "exec")


def test_cleans_whitespace_only_lines() -> None:
    module = _load_script()
    source = "value = 1\n    \nnext_value = 2\n"

    updated = module.clean_blank_lines(source)

    assert updated == "value = 1\n\nnext_value = 2\n"


def test_collapses_blank_lines_at_end_of_file() -> None:
    module = _load_script()

    updated = module.clean_blank_lines("pass\n\n\n")

    assert updated == "pass\n"
