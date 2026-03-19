from shellgenius.gpt_integration import estimated_cost, format_prompt


def test_format_prompt_uses_bash_for_unix_shells():
    prompt = format_prompt("list files in the current directory", "Linux")

    assert prompt[0]["role"] == "system"
    assert "Linux" in prompt[0]["content"]
    assert prompt[1]["role"] == "user"
    assert "```bash" in prompt[1]["content"]
    assert "list files in the current directory" in prompt[1]["content"]


def test_format_prompt_uses_powershell_for_windows():
    prompt = format_prompt("list files in the current directory", "Windows")

    assert "```powershell" in prompt[1]["content"]


def test_estimated_cost_formats_to_six_decimals():
    assert estimated_cost(1234, 0.0015) == "0.001851"
