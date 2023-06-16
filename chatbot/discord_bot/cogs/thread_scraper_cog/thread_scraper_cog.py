import logging
from datetime import datetime

import discord
from discord.ext import commands

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.student_info.find_student_name import find_student_name
from chatbot.student_info.load_student_info import load_student_info, find_student_discord_id, \
    add_discord_id_if_necessary
from chatbot.system.environment_variables import get_admin_users, is_course_server
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

logger = logging.getLogger(__name__)

logging.getLogger('discord').setLevel(logging.INFO)
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
        try:
            if is_course_server(ctx.guild.id):
                student_info = load_student_info()
            else:
                student_info = None

            thread_count = 0

            # Make sure we're only responding to the admin users
            if not ctx.user.id in get_admin_users():
                logger.info(f"User {ctx.user_id} is not an admin user")
                return

            status_message = await ctx.author.send(
                f"Starting thread scraping process for server: {ctx.guild.name} on {datetime.now().isoformat()}\n___________\n")
            if full_server_backup:
                channels = await ctx.guild.fetch_channels()
                logger.info(f"Saving all threads in server: {ctx.guild.name}")
            else:
                channels = [ctx.channel]
                logger.info(f"Saving all threads in channel: {ctx.channel.name}")

            for channel in channels:
                if isinstance(channel, discord.TextChannel):  # If this is a text channel
                    for thread in channel.threads:  # Loop through each thread

                        thread_count += 1
                        saving_thread_string = f"{thread_count}: Channel:`{str(channel)}`:{thread.jump_url}"
                        logger.info(saving_thread_string)

                        update_status_message_string = status_message.content + f"\n{saving_thread_string}"
                        number_of_characters_in_status_message = len(update_status_message_string)
                        print(f"Number of characters in status message: {number_of_characters_in_status_message}")
                        if number_of_characters_in_status_message>= 1900:
                            print(f"Sending new message because {number_of_characters_in_status_message} characters")
                            status_message = await ctx.author.send("`--2000 character limit reached, sending new message--`")
                            update_status_message_string = f"---\n{saving_thread_string}"

                        status_message = await  status_message.edit(content=update_status_message_string)

                        thread_owner_username = thread.name.split("'")[0]

                        student_discord_username, student_name = find_student_name(thread_owner_username)
                        student_discord_id = find_student_discord_id(context=ctx,
                                                                     discord_username=student_discord_username)
                        if student_discord_id is None:
                            logger.info(f"Could not find student discord id for {student_discord_username}")
                            student_discord_id = 0
                        if student_name in student_info:
                            add_discord_id_if_necessary(student_discord_id=student_discord_id,
                                                        student_info=student_info,
                                                        student_name=student_name, )

                        mongo_query = {
                            "_student_name": student_name,
                            "_student_username": student_discord_username,
                            "server_name": ctx.guild.name,
                            "discord_user_id": student_discord_id,
                            "thread_title": thread.name,
                            "thread_id": thread.id,
                            "thread_url": thread.jump_url,
                            "created_at": thread.created_at,
                            "channel": channel.name,
                        }

                        thread_as_list_of_strings = []
                        character_count_for_this_thread_total = 0
                        character_count_for_this_thread_student = 0
                        async for message in thread.history(limit=None, oldest_first=True):
                            message_content = message.content
                            if message_content == '':
                                continue
                            message_author_str = str(message.author)
                            thread_as_list_of_strings.append(f"{message_author_str} said: '{message_content}'")
                            message_length = len(message_content)
                            character_count_for_this_thread_total += message_length

                            if message.author.id != self.bot.user.id:
                                character_count_for_this_thread_student += message_length

                            messsage_update_package = {
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
                                "total_message_count": thread.message_count,
                                'mongo_entry_updated': datetime.now().isoformat(sep='T')

                            }

                            self.mongo_database_manager.upsert(
                                collection_name=get_thread_backups_collection_name(server_name=message.guild.name),
                                query=mongo_query,
                                data={"$addToSet": {"messages": messsage_update_package},
                                      "$set": {
                                          "thread_as_list_of_strings": thread_as_list_of_strings,
                                          "thread_as_one_string": "\n".join(thread_as_list_of_strings),
                                          "total_character_count_for_this_thread": character_count_for_this_thread_total,
                                          "character_count_for_this_thread_student": character_count_for_this_thread_student,
                                      }
                                      }
                            )
        except Exception as e:
            print(f"Exception in scrape_threads: {e}")
            logger.exception(e)
            raise e