import os

import pytest

from shellgenius.cli import DEFAULT_MODEL
from shellgenius.gpt_integration import chatgpt_request, format_prompt

pytestmark = pytest.mark.real


def _require_openai_api_key():
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY is required for real smoke tests")


def _assert_shellgenius_response_shape(text: str) -> None:
    assert text.startswith("```bash\n")
    assert "\n```" in text


def test_default_model_real_smoke_non_streaming():
    _require_openai_api_key()

    generated_text, _, _ = chatgpt_request(
        format_prompt("print ok", "Linux"),
        model=DEFAULT_MODEL,
        stream=False,
    )

    _assert_shellgenius_response_shape(generated_text)


@pytest.mark.parametrize("model", ["gpt-5.4-mini", "gpt-5.4"])
def test_gpt_5_4_family_real_smoke_streaming(model):
    _require_openai_api_key()

    chunks = []
    generated_text, _, _ = chatgpt_request(
        format_prompt("print ok", "Linux"),
        model=model,
        stream=True,
        chunk_callback=chunks.append,
    )

    _assert_shellgenius_response_shape(generated_text)
    assert chunks
