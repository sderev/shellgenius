### Changed

* Add `--model`, `--no-stream`, `--plain`, `--command-only`, `--execute`, and `--yes` to the CLI.
* Make the default flow print the generated command and exit unless `--execute` is passed.
* Make non-TTY output plain and buffered by default, and require `--yes` for non-interactive execution.
* Reject non-shell fenced model output in `--command-only` and `--execute`.
* Make `--execute` honor the fenced shell language, and reject shell fences that do not match the current platform.
