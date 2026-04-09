# Changelog

## Unreleased

<!-- scriv-insert-here -->

<a id='changelog-0.2.0'></a>
## 0.2.0 — 2026-04-08

### Removed

* `-y`/`--yes` and `-x`/`--execute` flags. Execution now requires the interactive confirmation prompt (`Execute this command? [y/N]`). Piped stdin is supported when `stdout` is a TTY (e.g., `printf 'y\n' | shellgenius "task"`).

### Added

* Built-in `alabaster` code block theme (light palette derived from [alabaster.vim](https://github.com/sderev/alabaster.vim)). Set `"code_block_theme": "alabaster"` in `~/.config/lmt/config.json`.

* `shellgenius key set` and `shellgenius key edit` manage the OpenAI API key stored in `~/.config/lmt/key.env`.
* API key is now loaded from the `OPENAI_API_KEY` environment variable first, then from `~/.config/lmt/key.env`. The key file accepts `OPENAI_API_KEY=...`, `export OPENAI_API_KEY=...`, or a bare key.
* Key file writes use `0600` permissions.
* Missing-key errors now print actionable guidance.

* Rich output now honors `code_block_theme` and `inline_code_theme` from `~/.config/lmt/config.json` (`lmterminal` compatibility).

* `shellgenius models` lists supported models and their short aliases.
* `-m`/`--model` now validates model names and resolves aliases (e.g., `-m 4.1` maps to `gpt-4.1`). Invalid names are rejected with a pointer to `shellgenius models`.

* Checked-in bash and zsh completion scripts for `shellgenius`, with README setup instructions for generated or static shell completion.

* `--tokens` flag to print prompt token count and estimated cost, with colored output: token count in yellow, model name in blue, cost in yellow.

### Changed

* Rename `--plain` to `--raw` (`-r`), add `--rich` (`-R`), and promote `--cmd` as the primary command-only flag (`--command-only` remains as a hidden alias). Non-TTY `stdout` now defaults to bare command output after ShellGenius verifies the fenced shell can run on the current platform, while `--rich` falls back to plain-text output there.
* `shellgenius --help` now shows the default prompt options alongside the `models` and `key` commands.

* ShellGenius now defaults to `gpt-5.4-mini`.

* `shellgenius` now prints the suggested command inside a fenced shell code block before the explanation, matching the format the CLI executes.

* README installation section recommends `uv tool install` instead of `pipx`.

* `shellgenius --rich` now falls back to plain-text output when `stdout` is not a TTY. `--raw --rich` is still rejected as a conflicting option pair.

* `shellgenius.theme` now controls ShellGenius-specific command-block rendering separately from the shared top-level `code_block_theme`, so ShellGenius can use its `alabaster` command block without changing `lmterminal`'s shared syntax theme.
* Rich TTY output now keeps that ShellGenius command-block renderer during streaming, preserves one blank line above and below the command inside the block, and `inline_code_theme` now styles visible inline code instead of falling back to Rich's default inline-code palette.
* The built-in `alabaster` preset now uses the upstream list-marker yellow for explanation bullets instead of the comments-and-errors red.

* Rich output now supports a nested `shellgenius` theme block in `~/.config/lmt/config.json`, with built-in presets and per-style Rich overrides on top of the legacy `code_block_theme` and `inline_code_theme` keys.
* Built-in `alabaster` now uses its upstream `#f8f8f8` background again. If you want the old highlighted block background, add it explicitly with `shellgenius.styles`, for example `"markdown.code_block": "on #f0f0f0"`.

* `shellgenius` now asks whether to run the generated command when `stdout` is a TTY and stdin can answer the prompt. There is no flag to bypass the prompt; execution still requires explicit confirmation, while EOF stdin such as `</dev/null>` skips prompting and leaves the command unexecuted.
* Add a blank line before Rich-rendered markdown output for visual separation.

### Fixed

* `shellgenius key set` now exits non-zero when a key already exists.

* Invalid `--model` errors now use clearer Click-styled copy and point to `shellgenius models`.

* ShellGenius now exits cleanly without a Python traceback when interrupted with `Ctrl+C` very early during startup.

* Raw TTY output now leaves a blank line before the execution prompt, matching the Rich path.

* Malformed leaf subcommand calls such as `shellgenius models for me` and `shellgenius key set sk-...` now stay on the subcommand path and fail locally instead of falling back to prompt mode.
<!-- scriv-end-here -->
