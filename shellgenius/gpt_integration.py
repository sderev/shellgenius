import time

import tiktoken

from .openai_backend import RateLimitError, create_openai_backend

__all__ = ["RateLimitError", "chatgpt_request", "estimated_cost", "format_prompt"]


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
    # max_tokens=3600,
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


def num_tokens_from_string(string, model="gpt-3.5-turbo-0613"):
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print(
            "Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming"
            " gpt-3.5-turbo-0613."
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif model == "gpt-4":
        print("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    elif model == "gpt-3.5-turbo-0613":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0613":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def estimated_cost(num_tokens, price_per_1k_tokens):
    """Returns the estimated cost of a number of tokens."""
    return f"{num_tokens / 1000 * price_per_1k_tokens:.6f}"


def estimate_prompt_cost(message):
    """Returns the estimated cost of a prompt."""
    num_tokens = num_tokens_from_messages(message)

    prices = {
        "gpt-3.5-turbo": 0.0015,
        "gpt-3.5-turbo-0613": 0.0015,
        "gpt-3.5-turbo-16k": 0.003,
        "gpt-4": 0.03,
        "gpt-4-0613": 0.03,
        "gpt-4-32k": 0.06,
        "gpt-4-32k-0613": 0.06,
    }

    return {model: estimated_cost(num_tokens, price) for model, price in prices.items()}
