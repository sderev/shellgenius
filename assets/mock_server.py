#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

RESPONSES = {
    "convert input.mp4 to better quality": """```bash
output="output.mp4"
ffmpeg -i "input.mp4" \
  -c:v libx264 -preset "slow" -crf 18 \
  -map 0 -c:a copy -movflags "+faststart" \
  "$output"
```

Explanation:
* Re-encodes `input.mp4` to H.264 with a quality-focused CRF setting.
* Uses `-preset "slow"` and `-crf 18` to trade encoding time for better visual quality.
* Keeps every mapped stream with `-map 0`, copies audio without another lossy pass, and writes `output.mp4` with `+faststart`.

""",
    "convert input.mov to a 1080p h.264 mp4 with aac audio": """```bash
ffmpeg -i input.mov -vf "scale=-2:1080" -c:v libx264 -preset slow -crf 20 -c:a aac -b:a 192k output.mp4
```

Explanation:
* Scales the video to 1080 pixels tall and keeps the width even for H.264.
* Encodes video with `libx264`, `-preset slow`, and `-crf 20` for a quality-focused export.
* Re-encodes audio as AAC at `192k`, which is a common web delivery setting.
""",
    "extract frames from video.mp4 every 5 seconds": """```bash
ffmpeg -i video.mp4 -vf "fps=1/5" frame_%04d.jpg
```

Explanation:
* Samples `video.mp4` at one frame every five seconds.
* Keeps the interval explicit with `-vf "fps=1/5"`.
* Writes numbered JPEG files as `frame_%04d.jpg`.
""",
    "make a pdf from all jpg images in this directory": """```bash
output="photos.pdf"
img2pdf ./*.jpg --output "$output"
```

Explanation:
* Collects every `*.jpg` file in the current directory and writes them to `photos.pdf`.
* Keeps the output filename explicit without making the command noisy.
* Uses `img2pdf`, which is built specifically for image-to-PDF conversion.

""",
    "show disk usage for each top-level folder here": """```bash
du -sh -- */ | sort -h
```

Explanation:
* Measures each immediate subdirectory in the current directory.
* Uses human-readable sizes and sorts them from smallest to largest.
* Gives a quick storage overview before you dig deeper.

""",
}

DEFAULT_RESPONSE = """```bash
pwd
```

Explanation:
* Prints the current working directory.
"""


def _extract_prompt(payload: dict) -> str:
    input_items = payload.get("input")
    if isinstance(input_items, list):
        for item in reversed(input_items):
            content = item.get("content")
            if isinstance(content, str):
                return content

    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        content = messages[-1].get("content")
        if isinstance(content, str):
            return content

    return ""


def _lookup_response(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for needle, response in RESPONSES.items():
        if needle.lower() in prompt_lower:
            return response
    return DEFAULT_RESPONSE


class MockOpenAIHandler(BaseHTTPRequestHandler):
    server_version = "ShellGeniusDemo/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"ok": True})
            return

        if self.path == "/v1/models":
            self._send_json({"data": [{"id": "gpt-5.4-mini"}]})
            return

        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "invalid json")
            return

        prompt = _extract_prompt(payload)
        text = _lookup_response(prompt)

        if self.path == "/v1/responses":
            self._send_responses_api(text)
            return

        if self.path == "/v1/chat/completions":
            self._send_chat_completions(text)
            return

        self.send_error(404)

    def _send_responses_api(self, text: str) -> None:
        response = {
            "id": "resp_demo",
            "object": "response",
            "status": "completed",
            "model": "gpt-5.4-mini",
            "output": [
                {
                    "id": "msg_demo",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text, "annotations": []}],
                }
            ],
            "output_text": text,
        }
        self._send_json(response)

    def _send_chat_completions(self, text: str) -> None:
        response = {
            "id": "chatcmpl_demo",
            "object": "chat.completion",
            "created": 1,
            "model": "gpt-5.4-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        }
        self._send_json(response)

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = HTTPServer(("127.0.0.1", port), MockOpenAIHandler)
    print(f"Mock server listening on http://127.0.0.1:{port}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
