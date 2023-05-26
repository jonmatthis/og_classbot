import logging

import discord
from discord.ext import commands

from chatbot.system.environment_variables import get_admin_users

logger = logging.getLogger(__name__)

def create_collection_name(server_name:str):
    return f"thread_backups_for_{server_name}"
class ThreadScraperCog(commands.Cog):
    def __init__(self, bot, mongo_database):
        self.bot = bot
        self.mongo_database = mongo_database

    @discord.slash_command(name='scrape_threads', description='(ADMIN ONLY) Scrape all threads in the current server')
    async def scrape_threads(self, ctx: discord.ApplicationContext):
        # Make sure we're only responding to the admin users
        if not ctx.user.id in get_admin_users():
            logger.info(f"User {ctx.user_id} is not an admin user")
            return
        channels = await ctx.guild.fetch_channels()
        for channel in channels:
            if isinstance(channel, discord.TextChannel):  # If this is a text channel
                for thread in channel.threads:  # Loop through each thread
                    logger.info(f"Saving thread: {thread.name} to mongo database")
                    thread_owner_name = thread.name.split("'")[0]
                    async for message in thread.history(limit=None, oldest_first=True):  # Get all messages in the thread
                        self.mongo_database.upsert(
                            collection=create_collection_name(server_name=message.guild.name),
                            query={"server_name": message.guild.name,
                                   "thread_owner_name": thread_owner_name,
                                   "thread_title": thread.name,
                                   "created_at": thread.created_at,
                                   "channel": channel.name},
                            data={"$push": {"messages": {
                                'author': str(message.author),
                                'author_id': message.author.id,
                                'user_id': message.author.id,
                                'content': message.content,
                                'timestamp': message.created_at.isoformat(),
                                'channel': message.channel.name,
                                'jump_url': message.jump_url,
                                'thread': message.thread if message.thread else 'None',
                                'dump': str(message)
                            }}}
                        )
