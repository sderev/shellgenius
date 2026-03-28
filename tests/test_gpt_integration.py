from types import SimpleNamespace

import httpx
import pytest
from openai import RateLimitError

import shellgenius.api_key as api_key_module
from shellgenius.gpt_integration import (
    chatgpt_request,
    estimate_prompt_cost,
    format_prompt,
    num_tokens_from_messages,
)
from shellgenius.openai_backend import (
    OpenAIResponsesBackend,
    prepare_prompt_for_responses_api,
)


class FakeCreateAPI:
    def __init__(self, *, response=None, error=None):
        self._response = response
        self._error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class FakeOpenAIClient:
    def __init__(
        self,
        *,
        response=None,
        error=None,
        chat_response=None,
        chat_error=None,
    ):
        self.responses = FakeCreateAPI(response=response, error=error)
        self.chat = SimpleNamespace(
            completions=FakeCreateAPI(response=chat_response, error=chat_error)
        )


def test_format_prompt_uses_bash_for_unix_shells():
    prompt = format_prompt("list files in the current directory", "Linux")

    assert prompt[0]["role"] == "system"
    assert "Linux" in prompt[0]["content"]
    assert "same language as the user" in prompt[0]["content"]
    assert prompt[1]["role"] == "user"
    assert "```bash" in prompt[1]["content"]
    assert "Do not write anything before the code block." in prompt[1]["content"]
    assert "list files in the current directory" in prompt[1]["content"]


def test_format_prompt_uses_powershell_for_windows():
    prompt = format_prompt("list files in the current directory", "Windows")

    assert "```powershell" in prompt[1]["content"]


def test_prepare_prompt_for_responses_api_preserves_system_messages_in_order():
    prepared = prepare_prompt_for_responses_api(
        [
            {"role": "system", "content": "Talk like a pirate."},
            {"role": "user", "content": "List files."},
            {"role": "assistant", "content": "Aye."},
            {"role": "system", "content": "Stay concise."},
        ]
    )

    assert prepared.instructions is None
    assert prepared.input == [
        {
            "type": "message",
            "role": "system",
            "content": "Talk like a pirate.",
        },
        {
            "type": "message",
            "role": "user",
            "content": "List files.",
        },
        {
            "type": "message",
            "role": "assistant",
            "content": "Aye.",
        },
        {
            "type": "message",
            "role": "system",
            "content": "Stay concise.",
        },
    ]


def test_chatgpt_request_returns_non_streaming_response(monkeypatch):
    fake_response = SimpleNamespace(output_text="```bash\nls\n```")
    fake_backend = SimpleNamespace(
        calls=[],
        create_text_response=lambda **kwargs: (
            fake_backend.calls.append(kwargs) or ("```bash\nls\n```", fake_response)
        ),
    )

    monkeypatch.setattr("shellgenius.gpt_integration.create_openai_backend", lambda: fake_backend)

    generated_text, response_time, response = chatgpt_request(
        format_prompt("list files in the current directory", "Linux")
    )

    assert generated_text == "```bash\nls\n```"
    assert response is fake_response
    assert response_time >= 0
    assert fake_backend.calls[0]["stream"] is False


def test_openai_backend_collects_streaming_response_and_calls_chunk_callback():
    stream = [
        SimpleNamespace(type="response.output_text.delta", delta="```bash\n"),
        SimpleNamespace(type="response.output_text.delta", delta="ls\n"),
        SimpleNamespace(type="response.output_text.delta", delta="```"),
        SimpleNamespace(
            type="response.completed",
            response=SimpleNamespace(output_text="```bash\nls\n```"),
        ),
    ]
    fake_client = FakeOpenAIClient(response=stream)
    backend = OpenAIResponsesBackend(client=fake_client)
    chunks = []

    generated_text, response = backend.create_text_response(
        prompt=format_prompt("list files in the current directory", "Linux"),
        model="gpt-5.4-mini",
        n=1,
        temperature=1,
        stop=None,
        stream=True,
        chunk_callback=chunks.append,
    )

    assert generated_text == "```bash\nls\n```"
    assert response == stream
    assert chunks == ["```bash\n", "ls\n", "```"]
    assert "instructions" not in fake_client.responses.calls[0]
    assert fake_client.responses.calls[0]["input"] == [
        {
            "type": "message",
            "role": "system",
            "content": format_prompt("list files in the current directory", "Linux")[0]["content"],
        },
        {
            "type": "message",
            "role": "user",
            "content": format_prompt("list files in the current directory", "Linux")[1]["content"],
        },
    ]


def test_openai_backend_ignores_empty_stream_deltas_and_uses_completed_text():
    stream = [
        SimpleNamespace(type="response.output_text.delta", delta=""),
        SimpleNamespace(
            type="response.completed",
            response=SimpleNamespace(output_text="```bash\nls\n```"),
        ),
    ]
    fake_client = FakeOpenAIClient(response=stream)
    backend = OpenAIResponsesBackend(client=fake_client)
    chunks = []

    generated_text, response = backend.create_text_response(
        prompt=format_prompt("list files in the current directory", "Linux"),
        model="gpt-5.4-mini",
        n=1,
        temperature=1,
        stop=None,
        stream=True,
        chunk_callback=chunks.append,
    )

    assert generated_text == "```bash\nls\n```"
    assert response == stream
    assert chunks == []


def test_openai_backend_preserves_mixed_prompt_order_for_responses_api():
    fake_client = FakeOpenAIClient(response=SimpleNamespace(output_text="done"))
    backend = OpenAIResponsesBackend(client=fake_client)
    prompt = [
        {"role": "system", "content": "First system message."},
        {"role": "user", "content": "Question."},
        {"role": "assistant", "content": "Prior answer."},
        {"role": "system", "content": "Second system message."},
    ]

    generated_text, response = backend.create_text_response(
        prompt=prompt,
        model="gpt-5.4-mini",
        n=1,
        temperature=1,
        stop=None,
        stream=False,
        chunk_callback=None,
    )

    assert generated_text == "done"
    assert response.output_text == "done"
    assert fake_client.responses.calls[0]["input"] == [
        {"type": "message", "role": "system", "content": "First system message."},
        {"type": "message", "role": "user", "content": "Question."},
        {"type": "message", "role": "assistant", "content": "Prior answer."},
        {"type": "message", "role": "system", "content": "Second system message."},
    ]
    assert "instructions" not in fake_client.responses.calls[0]


def test_openai_backend_falls_back_to_chat_completions_for_n_without_stop():
    chat_response = SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content="```bash\nls\n```")),
            SimpleNamespace(message=SimpleNamespace(content="```bash\npwd\n```")),
        ]
    )
    fake_client = FakeOpenAIClient(
        response=SimpleNamespace(output_text="unused"), chat_response=chat_response
    )
    backend = OpenAIResponsesBackend(client=fake_client)
    prompt = format_prompt("list files in the current directory", "Linux")

    generated_text, response = backend.create_text_response(
        prompt=prompt,
        model="gpt-5.4-mini",
        n=2,
        temperature=1,
        stop=None,
        stream=False,
        chunk_callback=None,
    )

    assert generated_text == "```bash\nls\n```"
    assert response is chat_response
    assert fake_client.responses.calls == []
    assert fake_client.chat.completions.calls == [
        {
            "messages": prompt,
            "model": "gpt-5.4-mini",
            "n": 2,
            "stream": False,
            "temperature": 1,
        }
    ]


@pytest.mark.parametrize("model", ["gpt-5.4-mini", "gpt-5.4", "GPT-5.4", " gpt-5.4-mini "])
def test_openai_backend_rejects_stop_for_gpt_5_4_models_before_api_call(model):
    fake_client = FakeOpenAIClient(response=SimpleNamespace(output_text="unused"))
    backend = OpenAIResponsesBackend(client=fake_client)

    with pytest.raises(
        ValueError,
        match=r"`stop` is not supported for GPT-5\.4 models",
    ):
        backend.create_text_response(
            prompt=format_prompt("list files in the current directory", "Linux"),
            model=model,
            n=1,
            temperature=1,
            stop=["STOP"],
            stream=False,
            chunk_callback=None,
        )

    assert fake_client.responses.calls == []
    assert fake_client.chat.completions.calls == []


def test_openai_backend_propagates_rate_limit_errors():
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request)
    fake_client = FakeOpenAIClient(
        error=RateLimitError("rate limited", response=response, body={"error": {}})
    )
    backend = OpenAIResponsesBackend(client=fake_client)

    with pytest.raises(RateLimitError):
        backend.create_text_response(
            prompt=format_prompt("list files in the current directory", "Linux"),
            model="gpt-5.4-mini",
            n=1,
            temperature=1,
            stop=None,
            stream=False,
            chunk_callback=None,
        )


def test_num_tokens_from_messages_counts_standard_prompt():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello."},
    ]
    count = num_tokens_from_messages(messages)
    assert isinstance(count, int)
    assert count > 0


def test_estimate_prompt_cost_returns_string_for_known_model():
    messages = format_prompt("list files", "Linux")
    cost = estimate_prompt_cost(messages, "gpt-5.4-mini")
    assert cost is not None
    assert cost.startswith("0.")


def test_estimate_prompt_cost_returns_none_for_unknown_model():
    messages = format_prompt("list files", "Linux")
    assert estimate_prompt_cost(messages, "unknown-model") is None


def test_openai_backend_exits_cleanly_when_key_file_has_invalid_utf8(monkeypatch, tmp_path, capsys):
    key_file = tmp_path / "key.env"
    key_file.write_bytes(b"\xff")
    monkeypatch.setattr(api_key_module, "KEY_FILE_PATH", key_file)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="1"):
        OpenAIResponsesBackend()

    assert "No OpenAI API key found." in capsys.readouterr().err
