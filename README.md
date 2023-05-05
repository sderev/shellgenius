# ShellGenius

ShellGenius is an intuitive CLI tool designed to enhance your command-line experience by turning your task descriptions into efficient shell commands.

Powered by OpenAI's gpt-3.5-turbo AI model, ShellGenius generates accurate commands based on your input and provides step-by-step explanations to help you understand the underlying logic.

https://user-images.githubusercontent.com/24412384/236322725-435b92c6-6d33-421f-8662-7eb6355d3f64.mp4

## Table of Contents

* [Installation](#installation)
* [Usage](#usage)
* [Examples](#examples)
* [Limitations](#limitations)
* [Contributing](#contributing)
* [License](#license)

## Installation

Ensure you have Python 3.8 or later installed on your system. To install ShellGenius, use the following command:

```bash
pip install shellgenius
```

### Install via `pipx` (recommended)

`pipx` is an alternative package manager for Python applications. It allows you to install and run Python applications in isolated environments, preventing conflicts between dependencies and ensuring that each application uses its own set of packages. I recommend using `pipx` to install ShellGenius.

**First, install `pipx` if you haven't already:**

* On macOS and Linux:

  ```
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
  ```

Alternatively, you can use your package manager (`brew`, `apt`, etc.).

* On Windows:

  ```
  py -m pip install --user pipx
  py -m pipx ensurepath
  ```

**Once `pipx` is installed, you can install ShellGenius using the following command:**

```
pipx install shellgenius
```

### OpenAI API key

ShellGenius requires an OpenAI API key to function. You can obtain a key by signing up for an account at [OpenAI's website](https://platform.openai.com/account/api-keys).

Once you have your API key, set it as an environment variable:

* On macOS and Linux:

  ```bash
  export OPENAI_API_KEY="your-api-key-here"
  ```

* On Windows:

  ```
  setx OPENAI_API_KEY your_key
  ```

## Usage

To use ShellGenius, simply type `shellgenius` followed by a description of the task you want to perform:

```bash
shellgenius "description of your task"
```

*Note: The quotes are not necessary.*

The tool will generate a shell command based on your description, display it with an explanation, and prompt you to confirm if you want to execute the command.

## Examples

Here are some examples of ShellGenius in action:

### Create a file

```bash
shellgenius "create a new file called example.txt"
```

**Output:**

```markdown
touch example.txt

Explanation:
* touch command is used to create a new file if it doesn't exist
* example.txt is the name of the new file

Be careful with your answer.
Do you want to execute this command? [Y/n]: y
```
___

### Number of lines in a file

```bash
shellgenius "count the number of lines in a file called data.csv"
```

**Output:**

```markdown
wc -l data.csv

Explanation:
* wc is a word, line, and byte count utility
* -l flag counts the number of lines
* data.csv is the target file

Be careful with your answer.
Do you want to execute this command? [Y/n]: y
```

## Limitations

ShellGenius is powered by an AI model and may not always generate the most efficient or accurate commands. Exercise caution when executing commands, especially when working with sensitive data or critical systems.

## License

ShellGenius is released under the [MIT License](LICENSE).

___

<https://github.com/sderev/shellgenius>
