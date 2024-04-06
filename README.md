# Telegram Chat Bot

This is a simple Telegram Chat Bot that can be used to send messages to a Telegram group or channel.
It utilizes a Basic AI agent in order to respond to messages sent to the bot.
It works by building up a knowledge base of messages sent to the bot and then using that knowledge base to respond to
messages sent to the bot.
It also implements a function interface for the bot to use in order to respond to messages that require further
information.
It utilizes [Libertai's decentralized LLM API](https://libertai.io/apis/text-generation/) for generating context-aware responses to user queries.
It specifically targets [Nouse Hermes 2 Pro](https://huggingface.co/NousResearch/Hermes-2-Pro-Mistral-7B) model for generating responses. This model is fine tuned for handling function calls.

## Requirements

- Python3 + virtualenv

## Setup

### Configuration

#### Note on Environment Variables

The bot is configured using environment variables.

It is best to do this in a `.env` file at the root of this repository. Our scripts will look for this file and use it to set the environment variables.

You can override the defaults you set in your `.env` by setting the environment variables with `export` prior to running the bot.

#### Telegram Bot Token

You must a valid Telegram Bot Token in order to use this bot. You can get one by talking to
the [BotFather](https://t.me/botfather) on Telegram.

Name this variable `TG_TOKEN` within your environment.

#### Logging

The logging is controlled by the `LOG_PATH` environment variable. This is the path to the log file that the bot will write to.

If this is not set, the bot will default to writing logs out to stdout only.

A good default is to set this to `./data/app.log` in the `.env` file.

#### Sqlite Database

The bot uses a sqlite database to store the knowledge base of messages that it has received.

The path to the database is controlled by the `DATABASE_PATH` environment variable. This variable should point to where our sqlite database is located.

NOTE: We explicitly don't set the full url because some tasks require `sqlite+aiosqlite` to be specified as the protocol. Rather than make the user specify this, we just ask for the path to the database file. `:memory:` is a valid option for this variable.

If this is not set, the bot will default to using `:memory:` which will create an in-memory database that will be lost when the bot is stopped.

A good default is to set this to `./data/app.db` in the `.env` file.

#### Debug Mode

If you want to run the bot in debug mode, you can set the `DEBUG` environment variable to `True`.

This will log debug events related to message handling. This is very useful when developming new features.

#### Agent

The bot uses an AI agent to generate responses to user queries.

See `./agent.yaml` for the default configuration. The bot will load this file and use it to configure the agent when it starts.

If you want to change the agent configuration, you can do so by editing this file or setting the `AGENT_CONFIG_PATH` environment variable to the path of the file you want to use. This file must contain a valid yaml configuration for the agent.

See `./agent.yaml` for the default configuration and documentation on the available options.

## Installation

This command sets up a virtual environment and installs the required dependencies within it for the bot to run.

```
./scripts/install.sh
```

If you would like to run the bot please ensure you use the virtual environment created by the install script.

```
source venv/bin/activate
python3 src/bot.py
```

## Usage

### Development

We provide a script to run the bot in development mode. This will run the bot in debug mode, against an in-memory database and write logs to stdout.

```
./scripts/dev.sh
```

All yopu have to do is make sure you have a valid Telegram Bot Token set in your environment as `TG_TOKEN`.

After you have launched the bot, you can search for it on Telegram using its username and start a conversation with it.

### Production-ish

#### Note on Database Migrations

The bot uses an sqlite database to store the knowledge base of messages that it has received.

You can use the `alembic` tool to manage the database schema. We provide scripts for doing so within the virtual environment.

You can run the following command to generate new migrations if you have made changes to the database schema:

```
./scripts/prepare_migrations.sh
```

This will generate a new migration file in the `./alembic/versions` directory.

Include these updated migrations in your pull request when you make changes to the database schema.

NOTE: This script is also controlled by the `DATABASE_PATH` environment variable. If you do not set this, the script will default to using `./data/app.db` as the database path.

You can run the following command to apply the migrations to the database:

```
./scripts/migrate.sh
```

This will apply any new migrations to the database.

Like the previous script, this script is also controlled by the `DATABASE_PATH` environment variable. If you do not set this, the script will default to using `./data/app.db` as the database path.

NOTE: the bot does not run migrations automatically. You must remember to responsibly run the `migrate.sh` script when you have new migrations to apply.

#### Running the Bot

We provide a script to run the bot in production mode. This will deactivate debug mode, and allow you to configure the logging and database path. If neither of these are set, the bot will default to writing logs to `./data/app.log` and using `/./data/app.db` as the database path.

```
./scripts/run.sh
```

NOTE: once again, it is your responsibility to set the `TG_TOKEN` environment variable and to run the `migrate.sh` script when you have new migrations to apply.
