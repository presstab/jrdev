#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Preparing environment for jrdev installation ---"
# Update package lists to ensure we can find packages in the Debian container.
apt-get update

# Install Python3, pip, and build essentials. The -y flag automatically answers yes.
# python3-venv is a good practice for ensuring the `build` module works correctly.
apt-get install -y python3 python3-pip python3-venv

echo "--- Installing Python build tools ---"
# Use python3's pip module to install the `build` package.
python3 -m pip install --upgrade pip build

pip install terminal-bench

# The harness places the agent source code (your jrdev project) in the
# working directory. We assume the current directory is the project root.
echo "--- Building jrdev wheel from source ---"
# Build the wheel using the standard build tool, which reads pyproject.toml.
git clone --branch termbench --single-branch https://github.com/presstab/jrdev
cd jrdev
pip install -e .

echo "--- Installing jrdev and its dependencies from the built wheel ---"
# Use pip to install the generated wheel. The wildcard '*' handles the
# dynamic version number in the filename (e.g., jrdev-0.1.7a0-py3-none-any.whl).
# This command also automatically installs all dependencies listed in setup.py.
#pip install dist/jrdev-*.whl

echo "--- jrdev installation complete ---"

# The abstract agent's `perform_task` method requires this exact string
# in the output to confirm a successful installation.
echo "INSTALL_SUCCESS"