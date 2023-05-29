from datetime import datetime

import discord
from discord.ext import commands


from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager


class SummarizerCog(commands.Cog):
    def __init__(self,
                 bot: discord.Bot,
                 mongo_database_manager: MongoDatabaseManager):
        self.bot = bot
        self.mongo_database_manager = mongo_database_manager


    @discord.slash_command(name='send_summary', description='Send user their stored summary and (optionally) threads')
    @discord.option(name="send_threads",
                    description="Whether or not to send the user all of their stored threads (vs just the summary)",
                    input_type=bool,
                    default=False)
    async def send_summary(self,
                           ctx: discord.ApplicationContext,
                           send_threads: bool = False):
        student_discord_username = str(ctx.author)
        student_profile = self.mongo_database_manager.get_student_profile(discord_username=student_discord_username)

        summary_send_message = await ctx.send(
            f"Sending summary for {student_discord_username} as of {datetime.now().isoformat()}...")
        if student_profile is None:
            await summary_send_message.edit(content=f"Could not find profile for user: {student_discord_username}...")
            await summary_send_message.add_reaction("❌")
            return

        student_summary = student_profile["student_summary"]
        if student_summary is None:
            await summary_send_message.edit(content=f"Could not find summary for user: {student_discord_username}...")
            await summary_send_message.add_reaction("❓")
            return
        await ctx.user.send(
            f"Summary for {student_discord_username} as of {datetime.now().isoformat()}:\n\n {student_summary}")
        await summary_send_message.edit(
            content=f"Successfully sent summary for {student_discord_username} as of {datetime.now().isoformat()}...")
        await summary_send_message.add_reaction("✅")

        if send_threads:
            student_threads = student_profile["threads"]
            thread_send_message = await ctx.send(
                f"Sending full conversation data for {student_discord_username} as of {datetime.now().isoformat()}...")

            if student_threads is None:
                await thread_send_message.edit(
                    content=f"Could not find threads for user: {student_discord_username}...")
                await thread_send_message.add_reaction("⁉️")
                return
            for thread in student_threads:
                thread_string = "\n".join(thread['thread_as_list_of_strings'])
                await ctx.user.send(
                    f"Thread from {thread['created_at']} titled {thread['thread_title']} :\n\n {thread_string}")

            await thread_send_message.edit(
                content=f"Successfully sent threads for {student_discord_username} as of {datetime.now().isoformat()}...")

