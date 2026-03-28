### Added

* `shellgenius key set` and `shellgenius key edit` manage the OpenAI API key stored in `~/.config/lmt/key.env`.
* API key is now loaded from the `OPENAI_API_KEY` environment variable first, then from `~/.config/lmt/key.env`. The key file accepts `OPENAI_API_KEY=...`, `export OPENAI_API_KEY=...`, or a bare key.
* Key file writes use `0600` permissions.
* Missing-key errors now print actionable guidance.

### Fixed

* `shellgenius key set` now exits non-zero when a key already exists.
