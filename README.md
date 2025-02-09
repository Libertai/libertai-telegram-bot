# LibertAI Telegram bot

This is a simple Telegram chatbot built using [our AI Agent framework](https://github.com/Libertai/libertai-agents) that
is able to assist users in DMs or groups.

It leverages [`pyTelegramBotAPI`](https://pypi.org/project/pyTelegramBotAPI/) with a small SQLite database for some
optimizations (storing the discussion history for better responses).

You can directly chat with the bot [here](https://t.me/liberchat_bot) or follow the instructions below to run it
locally.

## ⚙ Setup

### Environment variables

You have to define the following variables in a `.env` file at the root of the repository:

- `TELEGRAM_TOKEN`: You can get one by talking to the [BotFather](https://t.me/botfather) on Telegram.
- `DATABASE_PATH`: Should point to where the SQLite database is located (a good default is `./data/app.db`). If not set,
  it will default to `:memory:` which will create an in-memory database that will be lost when the bot is stopped.
- `LOG_PATH`: Path to the log file that the bot will write logs to (a good default is `./data/app.log`). If not set, the
  bot will default to writing logs out to stdout.
- `DEBUG`: Set to `True` to run in debug mode (will log debug events related to message handling, useful when developing
  new features)

### Installation

You need to have Python 3.10 (or newest) installed, with a virtualenv created to install dependencies:

```sh
python -m venv venv
source venv/bin/activate
poetry install
```

You can then run the bot with:

```sh
python3 src/bot.py
```
