# ShellGenius

ShellGenius is an intuitive CLI tool designed to enhance your command-line experience by turning your task descriptions into efficient shell commands.

Powered by OpenAI's gpt-3.5-turbo AI model, ShellGenius generates accurate commands based on your input and provides step-by-step explanations to help you understand the underlying logic.

<!-- TOC -->
## Table of Contents

1. [Video Demos](#video-demos)
    1. [Video Frames Extraction](#video-frames-extraction)
    1. [Directory Synchronization](#directory-synchronization)
1. [Installation](#installation)
    1. [Install via pipx (recommended)](#install-via-pipxhttpspypiorgprojectpipx-recommended)
    1. [OpenAI API key](#openai-api-key)
1. [Usage](#usage)
    1. [Regarding the Quotes](#regarding-the-quotes)
    1. [Creating an Alias](#creating-an-alias)
1. [Examples](#examples)
    1. [Remove Duplicate Lines](#remove-duplicate-lines)
    1. [Extract Columns in a File](#extract-columns-in-a-file)
    1. [Download a File](#download-a-file)
    1. [Number of Lines in a File](#number-of-lines-in-a-file)
1. [Limitations](#limitations)
1. [License](#license)
<!-- /TOC -->

## Video Demos

### Video Frames Extraction

https://github.com/sderev/shellgenius/assets/24412384/509ee15a-9804-41ad-ba31-3fdf02fc627f

### Directory Synchronization

https://github.com/sderev/shellgenius/assets/24412384/c9ad7560-cde3-4c68-aa89-b9bc4c9303f7

## Installation

Ensure you have Python 3.8 or later installed on your system. To install ShellGenius, use the following command:

```bash
python3 -m pip install shellgenius
```

### Install via [pipx](https://pypi.org/project/pipx/) (recommended)

`pipx` is an alternative package manager for Python applications. It allows you to install and run Python applications in isolated environments, preventing conflicts between dependencies and ensuring that each application uses its own set of packages. I recommend using `pipx` to install ShellGenius.

**First, install `pipx` if you haven't already**:

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

**Once `pipx` is installed, you can install ShellGenius using the following command**:

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

The tool will generate a shell command based on your description, display it with an explanation, and prompt you to confirm if you want to execute the command.

### Regarding the Quotes

The quotes are not necessary when the task description does not contain a single quote, or a special character.

**Not necessary**:

```bash
shellgenius compile and run myprogramm.cpp
```

**Necessary**:

```bash
shellgenius "find and replace 'oldtext' with 'newtext' in *.txt files"
```

### Creating an Alias

To further enhance the usability of ShellGenius, even with the presence of autocompletion, I recommend to create an alias for effortless access. One suggested alias is `??`.

By defining an alias, you can invoke ShellGenius simply by typing `??` followed by your task description, eliminating the need to type the full command each time.

To create the alias, add the following line to your shell configuration file (`~/.bashrc`, `~/.bash_profile`, or `~/.zshrc`, depending on your shell):

```bash
alias '??'='shellgenius'
```

After adding the alias, you can use ShellGenius by typing `??` instead of `shellgenius`, making your command-line experience even more seamless and efficient.

**Note**: Make sure to restart your shell or run `source ~/.bashrc` (or the corresponding file for your shell) for the alias to take effect.

## Examples

Here are some examples of ShellGenius in action:

### Remove Duplicate Lines

```bash
shellgenius "remove duplicate lines from file.txt"
```

**Output**:

```markdown
awk '!seen[$0]++' file.txt

Explanation:
* awk is a pattern scanning and processing language
* '!seen[$0]++' is an awk expression that removes duplicate lines
* file.txt is the name of the file to process

Be careful with your answer.
Do you want to execute this command? [Y/n]: y
```

___

### Extract Columns in a File

```bash
shellgenius "extract columns 1, 3, and 5 from data.csv"
```

**Output**:

```markdown
cut -d',' -f1,3,5 data.csv

Explanation:
* cut command is used to extract portions of lines from files
* -d',' specifies the delimiter as a comma
* -f1,3,5 specifies the columns to extract
* data.csv is the input CSV file

Be careful with your answer.
Do you want to execute this command? [Y/n]: y
```

___

### Download a File

```bash
shellgenius "download a file from https://example.com/file.zip"
```

**Output**:

```markdown
curl -OJL https://example.com/file.zip

Explanation:
* curl is a command-line tool for transferring data using various protocols
* -O option saves the downloaded file with its original name
* -J option tries to set the file name based on the URL
* -L option follows redirects if the URL points to a different location
* https://example.com/file.zip is the URL of the file to download

Be careful with your answer.
Do you want to execute this command? [Y/n]: y
```
___

### Number of Lines in a File

```bash
shellgenius "count the number of lines in a file called data.csv"
```

**Output**:

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
