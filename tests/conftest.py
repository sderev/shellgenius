import re

import pytest

REAL_MARK_PATTERN = re.compile(r"(?<![\w-])real(?![\w-])")


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run tests marked real",
    )


def _live_tests_requested(config):
    if config.getoption("--run-live"):
        return True

    markexpr = getattr(config.option, "markexpr", "") or ""
    return bool(REAL_MARK_PATTERN.search(markexpr))


def pytest_collection_modifyitems(config, items):
    if _live_tests_requested(config):
        return

    skip_real = pytest.mark.skip(reason="need --run-live option to run")
    for item in items:
        if "real" in item.keywords:
            item.add_marker(skip_real)
