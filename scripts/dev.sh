#!/bin/bash

source venv/bin/activate

source .env
export DATABASE_PATH=:memory:
export DEBUG=True
python3 -m src.main

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
