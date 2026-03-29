# Demo Assets

Regenerate the README demo GIF with:

```bash
assets/generate-demo.sh
```

The generator uses `assets/mock_server.py` so the output stays deterministic and does not call the live OpenAI API.

Requirements:

* `vhs`
* a local Chromium/Chrome binary, or an existing `chrome-debug` session

Browser note:

* `assets/generate-demo.sh` first tries a local Chromium/Chrome binary, including Playwright's cached Chromium.
* If no local browser is available, start `chrome-debug` once from this worktree and the generator will attach to that debug session instead.
