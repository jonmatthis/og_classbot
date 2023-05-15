import logging

from dotenv import load_dotenv

load_dotenv()

import discord

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

logger = logging.getLogger(__name__)



def make_discord_bot(mongo_database: MongoDatabaseManager):
    intents = discord.Intents.default()
    intents.message_content = True
    bot = discord.Bot(intents=intents)

    @bot.event
    async def on_ready():
        logger.info("Bot is ready!")
        print(f"{bot.user} is ready and online!")

    @bot.event
    async def on_message(message):
        logger.info(f"Received message: {message.content}")
        mongo_database.insert('messages', {
            'author': str(message.author),
            'author_id': message.author.id,
            'user_id': message.author.id,
            'content': message.content,
            'timestamp': message.created_at.isoformat(),
            'guild': message.guild.name if message.guild else 'DM',
            'channel': message.channel.name,
            'jump_url': message.jump_url,
            'thread': message.thread if message.thread else 'None',
            'dump': message.__str__(),
        })

    @bot.slash_command(name="hello", description="Say hello to the bot")
    async def hello(ctx):
        logger.info(f"Received hello command: {ctx}")
        await ctx.respond("Hey!")

    return bot
