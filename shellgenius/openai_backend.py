from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from openai import OpenAI, RateLimitError

PromptMessage = Mapping[str, str]
ChunkCallback = Callable[[str], None]

__all__ = [
    "ChunkCallback",
    "OpenAIResponsesBackend",
    "PreparedResponsesRequest",
    "PromptMessage",
    "RateLimitError",
    "create_openai_backend",
    "prepare_prompt_for_responses_api",
]


@dataclass(frozen=True, slots=True)
class PreparedResponsesRequest:
    instructions: str | None
    input: str | list[dict[str, str]]


def prepare_prompt_for_responses_api(prompt: Sequence[PromptMessage]) -> PreparedResponsesRequest:
    input_messages: list[dict[str, str]] = []

    for message in prompt:
        input_messages.append(
            {
                "type": "message",
                "role": message["role"],
                "content": message["content"],
            }
        )

    input_payload: str | list[dict[str, str]] = input_messages if input_messages else ""
    return PreparedResponsesRequest(instructions=None, input=input_payload)


class OpenAIResponsesBackend:
    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def create_text_response(
        self,
        *,
        prompt: Sequence[PromptMessage],
        model: str,
        n: int,
        temperature: float | None,
        stop: Any,
        stream: bool,
        chunk_callback: ChunkCallback | None,
    ) -> tuple[str, Any]:
        if stop is not None and _is_gpt_5_4_model(model):
            raise ValueError(
                "`stop` is not supported for GPT-5.4 models. Remove `stop` or use a "
                "model that supports it."
            )

        if n != 1 or stop is not None:
            return self._create_chat_completion_response(
                prompt=prompt,
                model=model,
                n=n,
                temperature=temperature,
                stop=stop,
                stream=stream,
                chunk_callback=chunk_callback,
            )

        request = prepare_prompt_for_responses_api(prompt)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "input": request.input,
            "stream": stream,
        }

        if request.instructions is not None:
            request_kwargs["instructions"] = request.instructions

        if temperature is not None:
            request_kwargs["temperature"] = temperature

        response = self._client.responses.create(**request_kwargs)

        if not stream:
            return response.output_text, response

        collected_events = []
        collected_text_parts: list[str] = []
        completed_response = None

        for event in response:
            collected_events.append(event)

            if getattr(event, "type", None) == "response.output_text.delta":
                delta = event.delta
                if not delta:
                    continue
                collected_text_parts.append(delta)
                if chunk_callback:
                    chunk_callback(delta)
            elif getattr(event, "type", None) == "response.completed":
                completed_response = getattr(event, "response", None)

        generated_text = "".join(collected_text_parts)
        if not generated_text and completed_response is not None:
            generated_text = completed_response.output_text

        return generated_text, collected_events

    def _create_chat_completion_response(
        self,
        *,
        prompt: Sequence[PromptMessage],
        model: str,
        n: int,
        temperature: float | None,
        stop: Any,
        stream: bool,
        chunk_callback: ChunkCallback | None,
    ) -> tuple[str, Any]:
        request_kwargs: dict[str, Any] = {
            "messages": list(prompt),
            "model": model,
            "n": n,
            "stream": stream,
        }

        if temperature is not None:
            request_kwargs["temperature"] = temperature

        if stop is not None:
            request_kwargs["stop"] = stop

        response = self._client.chat.completions.create(**request_kwargs)

        if not stream:
            return response.choices[0].message.content or "", response

        collected_chunks = []
        collected_text_parts: list[str] = []

        for chunk in response:
            collected_chunks.append(chunk)
            delta = chunk.choices[0].delta.content or ""
            collected_text_parts.append(delta)
            if chunk_callback and delta:
                chunk_callback(delta)

        return "".join(collected_text_parts), collected_chunks


def create_openai_backend() -> OpenAIResponsesBackend:
    return OpenAIResponsesBackend()


def _is_gpt_5_4_model(model: str) -> bool:
    normalized_model = model.strip().lower()
    return normalized_model == "gpt-5.4" or normalized_model.startswith("gpt-5.4-")
