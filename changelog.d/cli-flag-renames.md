### Changed

* Rename `--plain` to `--raw` (`-r`), add `--rich` (`-R`), and promote `--cmd` as the primary command-only flag (`--command-only` remains as a hidden alias). Non-TTY `stdout` now defaults to bare command output after ShellGenius verifies the fenced shell can run on the current platform, while `--rich` falls back to plain-text output there.
* `shellgenius --help` now shows the default prompt options alongside the `models` and `key` commands.
