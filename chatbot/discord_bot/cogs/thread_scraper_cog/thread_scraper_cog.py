import logging
from datetime import datetime

import discord
from discord.ext import commands

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.environment_variables import get_admin_users
from chatbot.system.filenames_and_paths import get_default_database_json_save_path, \
    get_thread_backups_collection_name
from chatbot.system.find_student_name import find_student_name
from chatbot.system.get_external_info import load_student_info

logger = logging.getLogger(__name__)


class ThreadScraperCog(commands.Cog):
    def __init__(self,
                 bot: discord.Bot,
                 mongo_database_manager: MongoDatabaseManager):
        self.bot = bot
        self.mongo_database_manager = mongo_database_manager
        self.student_info = load_student_info()

    @discord.slash_command(name='scrape_threads', description='(ADMIN ONLY) Scrape all threads in the current server')
    @discord.option(name="timestamp_backup",
                    description="Whether or not add a timestamp to the backup filename",
                    input_type=bool,
                    default=True)
    @discord.option(name="full_server_backup",
                    description="Whether or not to backup the entire server",
                    input_type=bool,
                    default=True)
    async def scrape_threads(self,
                             ctx: discord.ApplicationContext,
                             timestamp_backup: bool = True,
                             full_server_backup: bool = True,
                             ):
        # Make sure we're only responding to the admin users
        if not ctx.user.id in get_admin_users():
            logger.info(f"User {ctx.user_id} is not an admin user")
            return

        if full_server_backup:
            channels = await ctx.guild.fetch_channels()
            logger.info(f"Saving all threads in server: {ctx.guild.name}")
        else:
            channels = [ctx.channel]
            logger.info(f"Saving all threads in channel: {ctx.channel.name}")

        for channel in channels:
            if isinstance(channel, discord.TextChannel):  # If this is a text channel
                for thread in channel.threads:  # Loop through each thread
                    logger.info(f"Saving thread: {thread.name} to mongo database")

                    thread_owner_username = thread.name.split("'")[0]

                    student_discord_username, student_name = find_student_name(thread_owner_username)

                    mongo_query = {
                        "_student_name": student_name,
                        "_student_username": student_discord_username,
                        "server_name": ctx.guild.name,
                        "discord_user_id": ctx.author.id,
                        "thread_title": thread.name,
                        "created_at": thread.created_at,
                        "channel": channel.name,
                        "total_message_count": thread.message_count,
                    }

                    thread_as_list_of_strings = []
                    total_character_count_for_this_thread = 0
                    student_character_count_for_this_thread = 0
                    async for message in thread.history(limit=None, oldest_first=True):
                        message_content = message.content
                        if message_content == '':
                            continue
                        message_author_str = str(message.author)
                        thread_as_list_of_strings.append(f"{message_author_str} said: '{message_content}'")
                        message_length = len(message_content)
                        total_character_count_for_this_thread += message_length
                        if message_author_str == thread_owner_username:
                            student_character_count_for_this_thread += message_length

                        datebase_update_query = {
                            'author': message_author_str,
                            'author_id': message.author.id,
                            'user_id': message.author.id,
                            'content': message_content,
                            'channel': message.channel.name,
                            'jump_url': message.jump_url,
                            'created_at': message.created_at.isoformat(sep='T'),
                            'id': message.id,
                            'reactions': [str(reaction) for reaction in message.reactions],
                            'parent_message_id': message.reference.message_id if message.reference else '',
                            'number_of_characters': len(message_content),
                            'number_of_characters_from_the_student': student_character_count_for_this_thread,
                            'mongo_entry_updated': datetime.now().isoformat(sep='T')
                        }

                        self.mongo_database_manager.upsert(
                            collection=get_thread_backups_collection_name(server_name=message.guild.name),
                            query=mongo_query,
                            data={"$addToSet": {"messages": datebase_update_query},
                                  "$set": {
                                      "thread_as_list_of_strings": thread_as_list_of_strings,
                                      "total_character_count_for_this_thread": total_character_count_for_this_thread,
                                      "student_character_count_for_this_thread": student_character_count_for_this_thread,
                                  }
                                  }
                        )

        logger.info("Done scraping threads - saving database to disk")
        json_save_path = get_default_database_json_save_path(filename=f"{message.guild.name}_thread_backup.json",
                                                             timestamp=timestamp_backup)
        self.mongo_database_manager.save_json(
            collection_name=get_thread_backups_collection_name(server_name=message.guild.name),
            query={},
            save_path=json_save_path
        )
        logger.info(f"Done saving database to disk - {json_save_path}")

