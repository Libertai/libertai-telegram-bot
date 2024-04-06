#!/bin/bash

# Enter the virtual environment
source venv/bin/activate

echo "Running migrations..."

# Set the DATABASE_PATH environment variable
source .env

# If the DATABASE_PATH environment variable is not set, set a default value
if [ -z "$DATABASE_PATH" ]; then
	export DATABASE_PATH=./data/app.db
fi

echo "DATABASE_PATH: $DATABASE_PATH"

# Run the migrations
alembic upgrade head

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0

