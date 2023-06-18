from setuptools import setup, find_packages

VERSION = "0.1.10"


with open("README.md", encoding="UTF-8") as file:
    readme = file.read()

with open("requirements.txt", "r", encoding="utf-8") as file:
    requirements = [line.strip() for line in file]

setup(
    name="ShellGenius",
    description="ShellGenius is a tool to generate shell commands from description in natural language.",
    version=VERSION,
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "shellgenius = shellgenius.cli:shellgenius",
        ]
    },
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Sébastien De Revière",
)
