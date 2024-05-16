#!/bin/zsh

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the required packages
pip install -r requirements.txt

echo "Virtual environment setup complete. To activate it, run 'source venv/bin/activate'."
