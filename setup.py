#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="jrdev",
    version="0.1.0",
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
        "textual>=0.40.0"
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
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
)