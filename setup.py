#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Function to read the version from the VERSION file
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    with open(version_file, 'r') as f:
        return f.read().strip()

setup(
    name="jrdev",
    version=get_version(),
    description="JrDev terminal interface for LLM interactions",
    author="presstab",
    url="https://github.com/presstab/jrdev",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv",
        "pyreadline3; platform_system=='Windows'",
        "pydantic>=2.0.0",
        "textual[syntax]>=0.40.0",
        "tiktoken",
        "pyperclip"
    ],
    entry_points={
        "console_scripts": [
            "jrdev=jrdev.ui.textual_ui:run_textual_ui",
            "jrdev-cli=jrdev.__main__:run_cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    license='PolyForm Noncommercial License 1.0.0'
)
