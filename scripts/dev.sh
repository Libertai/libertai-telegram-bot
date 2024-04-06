#!/bin/bash

source venv/bin/activate

source .env
export DATABASE_PATH=:memory:
export DEBUG=True
export LOG_PATH=
python3 src/bot.py

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
