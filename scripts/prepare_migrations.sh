#!/bin/bash

# Enter the virtual environment
source venv/bin/activate

# Generate alembic migrations
echo "Generating migrations..."

# Set the DATABASE_URL environment variable
source .env

# If the DATABASE_URL environment variable is not set, set a default value
if [ -z "$DATABASE_PATH" ]; then
	export DATABASE_PATH=./data/app.db
fi

echo "DATABASE_PATH: $DATABASE_PATH"

# Generate alembic migrations
# Get the current datetime
now=$(date +"%Y_%m_%d_%H_%M_%S")
alembic revision --autogenerate -m "migration_$now"

# Deactivate the virtual environment
deactivate

# Exit the script
exit 0
