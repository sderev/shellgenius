### Changed

* Rich output now supports a nested `shellgenius` theme block in `~/.config/lmt/config.json`, with built-in presets and per-style Rich overrides on top of the legacy `code_block_theme` and `inline_code_theme` keys.
* Built-in `alabaster` now uses its upstream `#f8f8f8` background again. If you want the old highlighted block background, add it explicitly with `shellgenius.styles`, for example `"markdown.code_block": "on #f0f0f0"`.
