import logging
import os
from datetime import datetime

import discord

from chatbot.bots.assistants.course_assistant.course_assistant import CourseAssistant
from chatbot.bots.assistants.video_chatter.video_chatter import VideoChatter
from chatbot.discord_bot.cogs.chat_cog.chat_cog import Chat
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

TIME_PASSED_MESSAGE = """
> Some time passed and your memory of this conversation reset needed to be reloaded from the thread, but we're good now!
> 
> Provide the human with a brief summary of what you remember about them and this conversation so far.
"""

logger = logging.getLogger(__name__)

VIDEO_CHAT_CHANNEL_ID = 1116380746463060069


class VideoChatterCog(discord.Cog):
    def __init__(self,
                 bot: discord.Bot,
                 mongo_database_manager: MongoDatabaseManager):
        self._discord_bot = bot
        self._mongo_database = mongo_database_manager
        self._active_threads = {}
        self._allowed_channels = os.getenv("ALLOWED_CHANNELS").split(",")
        self._allowed_channels = [int(channel) for channel in self._allowed_channels]
        self._course_assistant_llm_chains = {}

    @discord.slash_command(name="video_chatter", description="Chat with the bot about a video!")
    async def chat(self,
                   ctx: discord.ApplicationContext):

        student_user_name = str(ctx.user)

        chat_title = self._create_chat_title_string(user_name=student_user_name)

        logger.info(f"Starting video_chatter thread {chat_title}")

        title_card_embed = await self._make_title_card_embed(str(ctx.user), chat_title)
        message = await ctx.send(embed=title_card_embed)

        await self._spawn_thread(message=message,
                                 student_user_name=student_user_name)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        logger.info(f"Received message: {message.content}")

        # Make sure we won't be replying to ourselves.
        if message.author.id == self._discord_bot.user.id:
            return

        if not message.channel.id == VIDEO_CHAT_CHANNEL_ID:
            logger.info(f"You can only talk with the VideoChatter in the video chat channel!")
            return

        # Only respond to messages in threads
        if not message.channel.__class__ == discord.Thread:
            return
        thread = message.channel
        # Only respond to messages in threads owned by the bot
        if not thread.owner_id == self._discord_bot.user.id:
            return

        # ignore if first character is ~
        if message.content[0] == "~":
            return
        try:
            chat = self._active_threads[thread.id]
        except KeyError:
            chat = await self._create_chat(thread=thread,
                                           student_discord_username=str(message.author)
                                           )

        logger.info(f"Sending message to the agent: {message.content}")

        await self._async_send_message_to_bot(chat=chat, input_text=message.content)

    async def _async_send_message_to_bot(self, chat: Chat, input_text: str):
        response_message = await chat.thread.send("`Awaiting bot response...`")
        try:

            async with response_message.channel.typing():
                bot_response = await chat.assistant.async_process_input(input_text=input_text)

            await response_message.edit(content=bot_response)

        except Exception as e:
            logger.error(e)
            await response_message.edit(content=f"Whoops! Something went wrong! 😅 \nHere is the error:\n ```\n{e}\n```")

    def _create_chat_title_string(self, user_name: str, task_type: str = None) -> str:
        return f"{user_name}'s chat about a video"

    async def _spawn_thread(self,
                            message: discord.Message,
                            student_user_name: str,
                            initial_text_input: str = None,
                            use_project_manager_prompt: bool = False
                            ):

        chat_title = self._create_chat_title_string(user_name=student_user_name)
        thread = await message.create_thread(name=chat_title)

        chat = await self._create_chat(thread=thread,
                                       student_discord_username=student_user_name,
                                       use_project_manager_prompt=use_project_manager_prompt)

        if initial_text_input is None:
            initial_text_input = f"A human has requested a chat!"

        if thread.message_count == 0:
            await chat.thread.send(
                embed=self._initial_message_embed(message=message, initial_message=initial_text_input))

        await self._async_send_message_to_bot(chat=chat,
                                              input_text=initial_text_input)

    async def _create_chat(self,
                           thread: discord.Thread,
                           student_discord_username: str) -> Chat:

        if thread.id in self._active_threads:
            logger.warning(f"Thread {thread.id} already exists! Returning existing chat")
            return self._active_threads[thread.id]

        assistant = await self._get_assistant(thread,
                                              student_discord_username=student_discord_username,
                                              )

        chat = Chat(
            title=self._create_chat_title_string(user_name=student_discord_username),
            thread=thread,
            assistant=assistant
        )

        self._active_threads[thread.id] = chat
        return chat

    async def _get_assistant(self,
                             thread: discord.Thread,
                             student_discord_username: str,
                             use_project_manager_prompt: bool = False) -> VideoChatter:

        assistant = VideoChatter()
        if thread.message_count > 0:
            message = await thread.send(
                f"> Reloading bot memory from thread history...")
            await assistant.load_memory_from_thread(thread=thread,
                                                    bot_name=str(self._discord_bot.user))

            await message.edit(content=f"> Bot memory loaded from thread history.")
        return assistant

    async def _make_title_card_embed(self, user_name: str, chat_title: str):
        return discord.Embed(
            title=chat_title,
            description=f"A conversation between {user_name} and the VideoChatter bot, started on {datetime.now()}",
            color=0x95d790,
        )

    def _initial_message_embed(self, message, initial_message):
        thread_intro = f"""
                   Remember! The bot...                   
                   ...ignores messages starting with ~                                
                   ...makes things up some times                    
                   ...cannot search the internet 
                   ...is doing its best 🤖❤️  
                   
                   Source code: 
                   https://github.com/jonmatthis/chatbot
                   This bot's prompt: 
                   https://github.com/jonmatthis/chatbot/blob/main/chatbot/assistants/course_assistant/course_assistant_prompt.py
                   
                   ------------------
                   ------------------
                   Beginning chat with initial message: 
                   
                   > {initial_message}
                    
                   """
        return discord.Embed(
            description=thread_intro,
            color=0x25d790,
        )
