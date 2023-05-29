import logging
from datetime import datetime

import discord
from discord.ext import commands
from langchain.text_splitter import CharacterTextSplitter

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

logger = logging.getLogger(__name__)

class SummarySenderCog(commands.Cog):
    def __init__(self,
                 bot: discord.Bot,
                 mongo_database_manager: MongoDatabaseManager):
        self.bot = bot
        self.mongo_database_manager = mongo_database_manager


    @discord.slash_command(name='send_summary', description='Send user their stored summary and (optionally) threads')

    async def send_summary(self,
                           ctx: discord.ApplicationContext):
        student_discord_username = str(ctx.author)
        logger.info(f"Sending summary for {student_discord_username}...")
        student_summary = self.mongo_database_manager.get_student_summary(discord_username=student_discord_username)

        summary_send_message = await ctx.send(
            f"Sending summary for {student_discord_username} as of {datetime.now().isoformat()}...")

        if student_summary is None:
            await summary_send_message.edit(content=f"Could not find summary for user: {student_discord_username}...")
            await summary_send_message.add_reaction("❓")
            return

        student_summary = student_summary.replace("```", "")
        text_splitter = CharacterTextSplitter(chunk_size=1900, chunk_overlap=0)
        student_summary_split = text_splitter.split_text(student_summary)
        for chunk_number, student_summary in enumerate(student_summary_split):
            await ctx.user.send(
                f"Summary for {student_discord_username} as of {datetime.now().isoformat()} \n"
                f"Chunk {chunk_number + 1} of {len(student_summary_split)}:\n"
                f"\n ```\n {student_summary}\n```\n")

        await summary_send_message.edit(
            content=f"Successfully sent summary for {student_discord_username} as of {datetime.now().isoformat()}...")
        await summary_send_message.add_reaction("✅")
