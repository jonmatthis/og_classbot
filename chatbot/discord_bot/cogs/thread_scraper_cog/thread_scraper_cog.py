import logging
import os
import re
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

from chatbot.discord_bot.cogs.thread_scraper_cog.message_anonymizer import anonymize_message
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.student_info.find_student_name import find_student_info
from chatbot.student_info.load_student_info import load_student_info
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
    @discord.option(name="anonymize",
                    description="Whether or not to anonymize the responses",
                    input_type=bool,
                    default=False)
    async def scrape_threads(self,
                             ctx: discord.ApplicationContext,
                             timestamp_backup: bool = True,
                             full_server_backup: bool = True,
                             anonymize: bool = False
                             ):

        if is_course_server(ctx.guild.id):
            student_info = load_student_info()
        else:
            student_info = None

        thread_count = 0

        collection_name = get_thread_backups_collection_name(server_name=ctx.guild.name)
        if anonymize:
            collection_name = "anonymized_" + collection_name

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
                threads = list(channel.threads)
                if len(threads) == 0:
                    logger.info(f"No threads in channel: {channel.name}")
                    continue

                async for message in channel.history():
                    if message.thread:
                        if not message.thread in threads:
                            threads.append(message.thread)

                for thread in threads:  # Loop through each thread

                    thread_count += 1
                    saving_thread_string = f"{thread_count}: Channel:`{str(channel)}`:{thread.jump_url}"
                    logger.info(saving_thread_string)

                    update_status_message_string = status_message.content + f"\n{saving_thread_string}"
                    number_of_characters_in_status_message = len(update_status_message_string)
                    print(f"Number of characters in status message: {number_of_characters_in_status_message}")
                    if number_of_characters_in_status_message >= 1900:
                        print(f"Sending new message because {number_of_characters_in_status_message} characters")
                        status_message = await ctx.author.send(
                            "`--2000 character limit reached, sending new message--`")
                        update_status_message_string = f"---\n{saving_thread_string}"

                    status_message = await  status_message.edit(content=update_status_message_string)

                    thread_owner_username = thread.name.split("'")[0]

                    student_discord_username, student_name, student_discord_id, student_uuid = find_student_info(
                        thread_owner_username)

                    mongo_query = {
                        "_student_name": student_name,
                        "_student_username": student_discord_username,
                        "_student_uuid": student_uuid,
                        "discord_user_id": student_discord_id,
                        "server_name": ctx.guild.name,
                        "thread_title": thread.name,
                        "thread_id": thread.id,
                        "thread_url": thread.jump_url,
                        "created_at": thread.created_at,
                        "channel": channel.name,
                    }

                    if anonymize:
                        mongo_query["_student_name"] = "REDACTED"
                        mongo_query["_student_username"] = "REDACTED"
                        mongo_query["discord_user_id"] = "REDACTED"
                        mongo_query["thread_title"] = "REDACTED"

                    thread_as_list_of_strings = []
                    word_count_for_this_thread_total = 0
                    word_count_for_this_thread_student = 0
                    character_count_for_this_thread_total = 0
                    character_count_for_this_thread_student = 0
                    green_check_emoji_present_in_thread = False
                    async for message in thread.history(limit=None, oldest_first=True):

                        message_author_str = str(message.author)

                        if anonymize:
                            message = anonymize_message(message)
                            if not message.author.id == self.bot.user.id:
                                message_author_str = student_uuid



                        message_content = message.content
                        if message_content == '':
                            continue

                        green_check_emoji_present_in_message = self.determine_if_green_check_present(message)
                        if green_check_emoji_present_in_message:
                            green_check_emoji_present_in_thread = True


                        thread_as_list_of_strings.append(f"{message_author_str} said: '{message_content}'")


                        message_word_count = len(message_content.split(' '))
                        word_count_for_this_thread_total += message_word_count
                        message_character_count = len(message_content)
                        character_count_for_this_thread_total += message_character_count

                        if message.author.id != self.bot.user.id:
                            word_count_for_this_thread_student += message_word_count
                            character_count_for_this_thread_student += message_character_count

                        messsage_update_package = {
                            'human': message.author.bot == self.bot.user.id,
                            'author': message_author_str,
                            'author_id': message.author.id,
                            'user_id': message.author.id,
                            'content': message_content,
                            'jump_url': message.jump_url,
                            'created_at': message.created_at.isoformat(sep='T'),
                            'id': message.id,
                            'reactions': [str(reaction) for reaction in message.reactions],
                            'parent_message_id': message.reference.message_id if message.reference else '',
                            "total_message_count": thread.message_count,
                            "green_check_emoji_present_in_message": green_check_emoji_present_in_message,
                        }

                        if anonymize:
                            messsage_update_package['author'] = "REDACTED"
                            messsage_update_package['author_id'] = "REDACTED"
                            messsage_update_package['user_id'] = "REDACTED"


                        await self.mongo_database_manager.upsert(
                            collection=collection_name,
                            query=mongo_query,
                            data={"$addToSet": {"messages": messsage_update_package},
                                  "$set": {
                                      "thread_as_list_of_strings": thread_as_list_of_strings,
                                      "thread_as_one_string": "\n".join(thread_as_list_of_strings),
                                      "total_word_count_for_this_thread": word_count_for_this_thread_total,
                                      "word_count_for_this_thread_student": word_count_for_this_thread_student,
                                      "total_character_count_for_this_thread": character_count_for_this_thread_total,
                                      "character_count_for_this_thread_student": character_count_for_this_thread_student,
                                      'mongo_entry_updated': datetime.now(),
                                      "green_check_emoji_present": green_check_emoji_present_in_thread,
                                  }
                                  }
                        )
        if timestamp_backup:
            load_dotenv()
            file_name = f"{ctx.guild.name}_thread_backup_{datetime.now().isoformat(sep='_')}.json"
            database_backup_path = os.getenv("PATH_TO_COURSE_DATABASE_BACKUPS")
            save_path = os.path.join(database_backup_path, file_name)
            if database_backup_path is None:
                raise Exception("PATH_TO_COURSE_DATABASE_BACKUPS not set in .env file")
            await self.mongo_database_manager.save_json(collection_name=collection_name,
                                                  save_path=save_path)

        await status_message.edit(content=f"Finished saving {thread_count} threads")
        print(f"Finished saving {thread_count} threads")

    def determine_if_green_check_present(self, message: discord.Message):
        reactions = message.reactions
        green_check_emoji_present = False

        if len(reactions) > 0:
            for reaction in reactions:
                if reaction.emoji == '✅':
                    print(message.content)
                    green_check_emoji_present = True
                    break

        if "Successfully sent summary" in message.content:
            # i forgot that I also put the checkmark on the "Successfully sent summary" message, but those dont count for this purpose
            green_check_emoji_present = False

        return green_check_emoji_present
