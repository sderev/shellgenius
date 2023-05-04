import os
import openai
import tiktoken
import time


def format_prompt(command_description):
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in using Unix-like OS and the shell terminal."
            ),
        },
        {
            "role": "user",
            "content": f"""
            I will give you a brief description of something I want to achieve in a Unix-like shell.
            I want you to answer with the command that matches the result I want to produce.
            The first line of your answer will be the said shell command.
            Then, I want you to explain it step by step with a bullet list.

            This is very important:
            * In absolutely no circumstance you are allowed to start your message by anything but the shell command. 

            To be absolutely clear, here is how your answer has to look like:
            ```bash
            command
            ```
            ### Explanation:
            * something
            * something
            * something
            ---
            {command_description}
            """,
        },
    ]
    return prompt


def chatgpt_request(
    prompt,
    model="gpt-3.5-turbo-0301",
    max_tokens=3600,
    n=1,
    temperature=0.5,
    stop=None,
    stream=False,
    chunk_callback=None,
):
    start_time = time.monotonic_ns()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Make the API request
    response = openai.ChatCompletion.create(
        messages=prompt,
        model=model,
        max_tokens=max_tokens,
        n=n,
        temperature=temperature,
        stop=stop,
        stream=stream,
    )

    if stream:
        # Create variables to collect the stream of chunks
        collected_chunks = []
        collected_messages = []

        # Iterate through the stream of events
        for chunk in response:
            collected_chunks.append(chunk)  # save the event response
            chunk_message = chunk["choices"][0]["delta"]  # extract the message
            collected_messages.append(chunk_message)  # save the message

            if chunk_callback: # call the callback with the chunk message
                chunk_callback(chunk_message.get("content", ""))
            # print(chunk_message.get("content", ""), end="")  # stream the message
        #print()
        response = collected_chunks

        # Save the time delay and text received
        response_time = (time.monotonic_ns() - start_time) / 1e9
        generated_text = "".join([m.get("content", "") for m in collected_messages])

    else:
        # Extract and save the generated response
        generated_text = response["choices"][0]["message"]["content"]

        # Save the time delay
        response_time = (time.monotonic_ns() - start_time) / 1e9

    return (
        generated_text,
        response_time,
        response,
    )


def num_tokens_from_string(string, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print(
            "Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming"
            " gpt-3.5-turbo-0301."
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print(
            "Warning: gpt-4 may change over time. Returning num tokens assuming"
            " gpt-4-0314."
        )
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
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
        "gpt-3.5-turbo-0301": 0.002,
        "gpt-4-0314": 0.03,
        "gpt-3.5-turbo": 0.002,
        "gpt-4-8k": 0.03,
        "gpt-4-32k": 0.06,
    }

    return {model: estimated_cost(num_tokens, price) for model, price in prices.items()}
