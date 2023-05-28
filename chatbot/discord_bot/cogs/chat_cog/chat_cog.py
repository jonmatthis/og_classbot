import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

import discord
from discord import Message
from pydantic import BaseModel

from chatbot.bots.assistants.course_assistant.course_assistant import CourseAssistant
from chatbot.bots.workers.student_profile_builder.student_profile_builder import StudentProfileBuilder
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.environment_variables import get_admin_users

logger = logging.getLogger(__name__)


class Chat(BaseModel):
    title: str
    thread: discord.Thread
    assistant: CourseAssistant

    started_at: str = datetime.now().isoformat()
    chat_id: str = uuid.uuid4()
    messages: List = []

    class Config:
        arbitrary_types_allowed = True


def get_assistant(assistant_type: str, **kwargs):
    if assistant_type == "introduction":
        return StudentProfileBuilder(**kwargs)

    return CourseAssistant(**kwargs)


class ChatCog(discord.Cog):
    def __init__(self,
                 bot: discord.Bot,
                 mongo_database: MongoDatabaseManager):
        self._discord_bot = bot
        self._mongo_database = mongo_database
        self._active_threads = {}
        self._allowed_channels = os.getenv("ALLOWED_CHANNELS").split(",")
        self._allowed_channels = [int(channel) for channel in self._allowed_channels]
        self._course_assistant_llm_chains = {}

    @discord.slash_command(name="chat", description="Chat with the bot")
    async def chat(self,
                   ctx: discord.ApplicationContext):

        if not ctx.channel.id in self._allowed_channels:
            logger.info(f"Channel {ctx.channel.id} is not allowed to start a chat")
            return

        chat_title = self._create_chat_title_string(str(ctx.user))
        logger.info(f"Starting chat {chat_title}")

        title_card_embed = await self._make_title_card_embed(str(ctx.user), chat_title)
        message_object = await ctx.send(embed=title_card_embed)

        await self._create_chat_thread(chat_title=chat_title,
                                       message_object=message_object,
                                       user_id=ctx.user.id,
                                       user_name=ctx.user.name,
                                       )

    @discord.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            # Make sure we won't be replying to ourselves.
            if payload.user_id == self._discord_bot.user.id:
                return

            # Make sure we're only responding to the correct emoji
            if not payload.emoji.name == '🧠':
                return

            # Make sure we're only responding to the admin users
            if not payload.user_id in get_admin_users():
                logger.info(f"User {payload.user_id} is not an admin user")
                return

            # Get the channel and message using the payload
            channel = self._discord_bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            await self._create_chat_thread(message_object=message,
                                           user_id=message.author.id,
                                           user_name=str(message.author),
                                           initial_message=message.content
                                           )

        except Exception as e:
            print(f'Error: {e}')

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        logger.info(f"Received message: {message.content}")

        # Make sure we won't be replying to ourselves.
        if message.author.id == self._discord_bot.user.id:
            return

        # Only respond to messages in threads
        if not message.channel.__class__ == discord.Thread:
            return

        # Only respond to messages in threads owned by the bot
        if not message.channel.owner_id == self._discord_bot.user.id:
            return

        # ignore if first character is ~
        if message.content[0] == "~":
            return


        chat = await self._get_or_create_chat(message=message)

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
            await response_message.edit(content=f"Oh no, something went wrong! \nHere is the error:\n ```\n{e}\n```")

    def _create_chat_title_string(self, user_name: str) -> str:
        return f"{user_name}'s chat with {self._discord_bot.user.name}"

    async def _create_chat_thread(self,
                                  message: discord.Message,
                                  initial_message: str = "A human has requested a chat, say hello!"
                                  ):



        chat = await self._get_or_create_chat(message=message)

        await chat.thread.send(f"<@{user_id}> is the thread owner.")
        await chat.thread.send(f"The bot is ready to chat! "
                               f"\n(bot ignores messages starting with ~)")


        await chat.thread.send(f"Beginning chat with initial message: \n"
                               f"```\n{initial_message}\n```\n------------------")

        await self._async_send_message_to_bot(chat=chat, input_text=initial_message)

    async def _get_or_create_chat(self, message: Message) -> Chat:
        if message.channel.id in self._active_threads:
            return self._active_threads[message.channel.id]

        user_name = str(message.channel.author)
        chat_title = self._create_chat_title_string(user_name=user_name)

        if not message.channel.__class__ == discord.Thread:
            thread = await message.create_thread(name=chat_title)
        else:
            thread = message.channel

        chat = Chat(
            title=chat_title,
            thread=thread,
            assistant=CourseAssistant()
        )
        self._active_threads[message.channel.id] = chat
        return chat


async def _make_title_card_embed(self, user_name: str, chat_title: str):
    return discord.Embed(
        title=chat_title,
        description=f"A conversation between {user_name} and the bot, started on {datetime.now()}",
        color=0x25d790,
    )
