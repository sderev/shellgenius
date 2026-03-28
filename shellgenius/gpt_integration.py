import time

import tiktoken

from .openai_backend import RateLimitError, create_openai_backend

__all__ = [
    "RateLimitError",
    "chatgpt_request",
    "estimate_prompt_cost",
    "format_prompt",
    "num_tokens_from_messages",
]


def format_prompt(command_description, os_name):
    shell_name = "powershell" if os_name == "Windows" else "bash"
    prompt = [
        {
            "role": "system",
            "content": (
                f"You write shell commands for {os_name}. Reply in the same language as the user."
            ),
        },
        {
            "role": "user",
            "content": f"""Return the command for this task in a {os_name} shell.

Rules:
* Start with exactly one fenced code block for the command.
* Use this fence info string: `{shell_name}`.
* Do not write anything before the code block.
* After the code block, add a short bullet-list explanation.
* Keep the command concise and correct.

Format:
```{shell_name}
<command>
```

Explanation:
* ...

Task:
{command_description}
""",
        },
    ]
    return prompt


def chatgpt_request(
    prompt,
    model="gpt-5.4-mini",
    n=1,
    temperature=1,
    stop=None,
    stream=False,
    chunk_callback=None,
):
    start_time = time.monotonic_ns()
    backend = create_openai_backend()
    generated_text, response = backend.create_text_response(
        prompt=prompt,
        model=model,
        n=n,
        temperature=temperature,
        stop=stop,
        stream=stream,
        chunk_callback=chunk_callback,
    )
    response_time = (time.monotonic_ns() - start_time) / 1e9

    return (
        generated_text,
        response_time,
        response,
    )


def num_tokens_from_messages(messages, model="gpt-5.4-mini"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_per_message = 3
    tokens_per_name = 1

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


# Prices in USD per 1M input tokens (only models exposed via VALID_MODELS).
_INPUT_PRICES_PER_1M: dict[str, float] = {
    "gpt-4.1": 2,
    "gpt-4.1-mini": 0.40,
    "gpt-4.1-nano": 0.10,
    "gpt-4o": 2.50,
    "gpt-4o-mini": 0.15,
    "gpt-5": 1.25,
    "gpt-5-mini": 0.25,
    "gpt-5-nano": 0.05,
    "gpt-5.4": 2.50,
    "gpt-5.4-mini": 0.75,
    "gpt-5.4-nano": 0.20,
}


def estimate_prompt_cost(messages, model="gpt-5.4-mini"):
    """Returns the estimated prompt cost as a string, or ``None`` if the price is unknown."""
    num_tokens = num_tokens_from_messages(messages, model)
    price = _INPUT_PRICES_PER_1M.get(model)
    if price is None:
        return None
    return f"{num_tokens / 10**6 * price:.6f}"
