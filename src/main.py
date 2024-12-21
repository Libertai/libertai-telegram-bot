import asyncio

from src.commands import register_commands
from src.config import config


async def main():
    config.LOGGER.info("Starting bot...")
    try:
        # Get the bot's username
        bot_info = await config.BOT.get_me()
        config.BOT_INFO = bot_info
        config.LOGGER.info(f"Bot started: {bot_info.username}")

        await register_commands()
        config.LOGGER.info("Commands registered")
        await config.BOT.polling()
    except Exception as e:
        config.LOGGER.error(f"An unexpected error occurred: {e}")
    finally:
        config.LOGGER.info("Stopping bot...")


if __name__ == "__main__":
    asyncio.run(main())
