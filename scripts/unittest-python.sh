#!/bin/bash
set -e

# Check if Python version is provided
PYTHON_VERSION=${PYTHON_VERSION:-"3.11.10"}  # Default to 3.11 if not specified

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo "Installing pyenv..."
    curl https://pyenv.run | bash
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
fi

# Install specific Python version if not already installed
if ! pyenv versions | grep -q $PYTHON_VERSION; then
    echo "Installing Python $PYTHON_VERSION"
    pyenv install $PYTHON_VERSION
fi

pyenv virtualenv $PYTHON_VERSION 
# Set local Python version
pyenv local $PYTHON_VERSION

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Verify Python version
python --version

# Install dependencies and run tests
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt -r requirements-test.txt
pytest -v

# Deactivate and cleanup
deactivate
