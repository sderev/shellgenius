### Changed

* `shellgenius` now asks whether to run the generated command when `stdout` is a TTY and stdin can answer the prompt. There is no flag to bypass the prompt; execution still requires explicit confirmation, while EOF stdin such as `</dev/null>` skips prompting and leaves the command unexecuted.
* Add a blank line before Rich-rendered markdown output for visual separation.

### Fixed

* Malformed leaf subcommand calls such as `shellgenius models for me` and `shellgenius key set sk-...` now stay on the subcommand path and fail locally instead of falling back to prompt mode.
