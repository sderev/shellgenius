### Changed

* `shellgenius.theme` now controls ShellGenius-specific command-block rendering separately from the shared top-level `code_block_theme`, so ShellGenius can use its `alabaster` command block without changing `lmterminal`'s shared syntax theme.
* Rich TTY output now keeps that ShellGenius command-block renderer during streaming, preserves one blank line above and below the command inside the block, and `inline_code_theme` now styles visible inline code instead of falling back to Rich's default inline-code palette.
* The built-in `alabaster` preset now uses the upstream list-marker yellow for explanation bullets instead of the comments-and-errors red.
