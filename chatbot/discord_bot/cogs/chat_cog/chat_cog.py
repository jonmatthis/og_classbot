import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

import discord
from pydantic import BaseModel

from chatbot.assistants.course_assistant.course_assistant import CourseAssistant
from chatbot.assistants.student_interview_assistant.student_interview_assistant import StudentInterviewAssistant
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.environment_variables import get_admin_users

logger = logging.getLogger(__name__)


class Chat(BaseModel):
    title: str
    owner: Dict[str, Any]
    thread: discord.Thread
    assistant: CourseAssistant

    started_at: str = datetime.now().isoformat()
    chat_id: str = uuid.uuid4()
    messages: List = []

    class Config:
        arbitrary_types_allowed = True


def get_assistant(assistant_type: str, **kwargs):
    if assistant_type == "introduction":
        return StudentInterviewAssistant(**kwargs)

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
            chat_title = self._create_chat_title_string(user_name=str(message.author))
            await self._create_chat_thread(chat_title=chat_title,
                                           message_object=message,
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

        # only respond to messages in threads we've seen before
        query_response = self._mongo_database.chat_history_collection.find_one({"thread_id": message.channel.id})
        if not query_response:
            return
        # ignore if first character is ~
        if message.content[0] == "~":
            return

        try:
            chat = self._active_threads[message.channel.id]
        except KeyError:
            chat = await self._create_chat(thread=message.channel,
                                           mongo_query=self._get_mongo_query(message))

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
                                  chat_title: str,
                                  message_object: discord.Message,
                                  user_id: int,
                                  user_name: str,
                                  initial_message: str = "A human has requested a chat, say hello!"
                                  ):

        thread = await message_object.create_thread(name=chat_title)

        chat = await self._create_chat(chat_title=chat_title,
                                       thread=thread,
                                       user_id=user_id,
                                       user_name=user_name,
                                       server_id=message_object.guild.id,
                                       server_name=message_object.guild.name)

        await chat.thread.send(f"<@{user_id}> is the thread owner.")
        await chat.thread.send(f"The bot is ready to chat! "
                               f"\n(bot ignores messages starting with ~)")
        self._active_threads[chat.thread.id] = chat

        await chat.thread.send(f"Beginning chat with initial message: \n"
                               f"```\n{initial_message}\n```\n------------------")

        await self._async_send_message_to_bot(chat=chat, input_text=initial_message)

    async def _create_chat(self,
                           chat_title: str,
                           thread: discord.Thread,
                           user_id: int,
                           user_name: str,
                           server_id: int,
                           server_name: str):
        chat = Chat(
            title=chat_title,
            owner={"id": user_id,
                   "name": user_name},
            thread=thread,
            assistant=CourseAssistant(mongo_collection=self._mongo_database.chat_history_collection,
                                      mongo_query={"user_id": user_id,
                                                   "user_name": user_name,
                                                   "server_name": server_name,
                                                   "server_id": server_id,
                                                   "thread_id": thread.id,
                                                   "thread_title": chat_title,
                                                   "start_time": datetime.now().isoformat()
                                                   }

                                      )
        )
        return chat

    async def _make_title_card_embed(self, user_name: str, chat_title: str):
        return discord.Embed(
            title=chat_title,
            description=f"A conversation between {user_name} and the bot, started on {datetime.now()}",
            color=0x25d790,
        )
