from __future__ import annotations

import importlib


def main() -> int | None:
    """Run the CLI with lazy imports so startup interrupts stay quiet."""
    try:
        cli_module = importlib.import_module("shellgenius.cli")
    except KeyboardInterrupt as error:
        raise SystemExit(130) from error
    return cli_module.shellgenius()
