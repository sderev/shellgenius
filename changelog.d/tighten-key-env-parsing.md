### Changed

* `~/.config/lmt/key.env` is now parsed as a dedicated ShellGenius key file. ShellGenius still accepts `OPENAI_API_KEY=...`, quoted values, and `export OPENAI_API_KEY=...`, but no longer accepts a bare key line or unrelated env assignments in that file.
