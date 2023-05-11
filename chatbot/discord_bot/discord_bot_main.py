import asyncio
import logging
import os

from dotenv import load_dotenv

from chatbot.discord_bot.cogs.chat_cog.chat_cog import ChatCog
from chatbot.discord_bot.utilities.bot_maker import make_discord_bot

load_dotenv()

logger = logging.getLogger(__name__)


async def main():
    discord_bot = make_discord_bot()
    discord_bot.add_cog(ChatCog(discord_bot=discord_bot))
    await discord_bot.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    logger.info("Starting bot...")
    asyncio.run(main())
