import asyncio

from src.commands import register_commands
from src.config import config


async def main():
    config.LOGGER.info("Starting bot...")
    try:
        # TODO: check if this is still needed
        # Get the bot's username and set the persona name
        # bot_info = await BOT.get_me()
        # LOGGER.info(f"Bot started: {bot_info.username}")
        # set_bot_name(bot_info.username)
        await register_commands()
        config.LOGGER.info("Commands registered")
        await config.BOT.polling()
    except Exception as e:
        config.LOGGER.error(f"An unexpected error occurred: {e}")
    finally:
        config.LOGGER.info("Stopping Bot...")
        # Close all open connections
        # await agent.clear_all_chats()


if __name__ == "__main__":
    asyncio.run(main())
