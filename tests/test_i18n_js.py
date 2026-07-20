"""Run the i18n.js unit test suite via node --test.

The JS tests (static/js/i18n.test.mjs) cover:
  - _resolve dot-path key resolution
  - _interpolate variable substitution
  - _t() function with real locale data (en.json, es.json)
  - Locale file structure parity

Skips when node is not on PATH.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

_REPO = Path(__file__).resolve().parent.parent
_TEST_JS = _REPO / "static" / "js" / "i18n.test.mjs"
_HAS_NODE = shutil.which("node") is not None


def _run_node_test(extra_args: Optional[list[str]] = None) -> subprocess.CompletedProcess:
    cmd = ["node", "--test", str(_TEST_JS)]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(_REPO),
        timeout=60,
    )
    return proc


pytestmark = pytest.mark.skipif(not _HAS_NODE, reason="node binary not on PATH")


def test_i18n_js_all_tests_pass():
    """Run the full i18n.test.mjs suite and verify all tests pass."""
    proc = _run_node_test()
    if proc.returncode != 0:
        # On failure, show both stdout and stderr
        msg = proc.stderr or proc.stdout
        # node --test outputs test names on stdout, failures on stderr
        print(proc.stdout)
        pytest.fail(f"node --test failed (exit {proc.returncode}):\n{proc.stderr}")
    assert proc.returncode == 0


def test_i18n_js_specific_test_by_name():
    """Run a single test within the suite using --test-name-pattern."""
    proc = _run_node_test(["--test-name-pattern", "i18n _resolve"])
    if proc.returncode != 0:
        pytest.fail(f"node --test --test-name-pattern failed:\n{proc.stderr}")
    assert proc.returncode == 0


def test_i18n_js_stdout_mentions_tests():
    """Sanity check: the output should mention test names."""
    proc = _run_node_test(["--test-name-pattern", "simple key"])
    assert proc.returncode == 0
    output = proc.stdout + proc.stderr
    assert "simple key" in output or "i18n" in output.lower()
