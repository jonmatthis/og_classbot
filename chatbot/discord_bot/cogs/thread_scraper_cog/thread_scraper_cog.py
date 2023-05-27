import logging

import discord
from discord.ext import commands

from chatbot.bots.workers.thread_summarizer import ThreadSummarizer
from chatbot.system.environment_variables import get_admin_users

logger = logging.getLogger(__name__)


def get_thread_backups_collection_name(server_name: str):
    return f"thread_backups_for_{server_name}"


class ThreadScraperCog(commands.Cog):
    def __init__(self, bot, mongo_database):
        self.bot = bot
        self.mongo_database = mongo_database

    @discord.slash_command(name='scrape_threads', description='(ADMIN ONLY) Scrape all threads in the current server')
    @discord.option(name="summarize_threads",
                    description="Whether or not to summarize the threads",
                    input_type=bool,
                    default=False)
    async def scrape_threads(self,
                             ctx: discord.ApplicationContext,
                             summarize_threads: bool = False):
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
                    mongo_query = {"server_name": ctx.guild.name,
                                   "thread_owner_name": thread_owner_name,
                                   "thread_title": thread.name,
                                   "created_at": thread.created_at,
                                   "channel": channel.name}

                    thread_as_list_of_strings = []

                    async for message in thread.history(limit=None, oldest_first=True):
                        message_content = message.content
                        thread_as_list_of_strings.append(f"{str(message.author)} said: '{message_content}'")
                        self.mongo_database.upsert(
                            collection=get_thread_backups_collection_name(server_name=message.guild.name),
                            query=mongo_query,
                            data={"$push": {
                                "messages": {
                                    'author': str(message.author),
                                    'author_id': message.author.id,
                                    'user_id': message.author.id,
                                    'content': message_content,
                                    'timestamp': message.created_at.isoformat(),
                                    'channel': message.channel.name,
                                    'jump_url': message.jump_url,
                                    'dump': str(message)
                                }
                            },
                                "$set": {
                                    "thread_as_list_of_strings": thread_as_list_of_strings
                                }
                            }
                        )
                    if summarize_threads:
                        logger.info("Generating thread summary")
                        thread_summary = await ThreadSummarizer(thread_as_list_of_strings).summarize()
                        logger.info(f"Saving thread summary to mongo database, summary: {thread_summary}")
                        self.mongo_database.upsert(
                            collection=get_thread_backups_collection_name(server_name=message.guild.name),
                            query=mongo_query,
                            data={
                                "$set": {
                                    "summary": thread_summary
                                }
                            }
                        )
