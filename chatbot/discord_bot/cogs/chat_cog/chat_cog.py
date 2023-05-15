import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

import discord
from pydantic import BaseModel

from chatbot.langchain_stuff.llm_chain.course_assistant import CourseAssistant
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

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


def get_assistant(assistant_type: str):
    if assistant_type == "default":
        return CourseAssistant()
    if assistant_type == "introduction":
        return IntroductionAssistant()


class ChatCog(discord.Cog):
    def __init__(self,
                 discord_bot: discord.Bot,
                 mongo_database: MongoDatabaseManager):
        self._discord_bot = discord_bot
        self._mongo_database = mongo_database
        self._active_threads = {}
        self._allowed_channels = os.getenv("ALLOWED_CHANNELS").split(",")
        self._allowed_channels = [int(channel) for channel in self._allowed_channels]
        self._course_assistant_llm_chains = {}

    @discord.slash_command(name="chat", description="Chat with the bot")
    async def chat(self,
                   ctx: discord.ApplicationContext):

        if not ctx.channel.id in self._allowed_channels:
            return

        chat_title = self._create_chat_title_string(str(ctx.user))
        logger.info(f"Starting chat {chat_title}")

        title_card_embed = await self._make_title_card_embed(str(ctx.user), chat_title)
        message_object = await ctx.send(embed=title_card_embed)

        await self._create_chat_thread(chat_title=chat_title,
                                       message_object=message_object,
                                       user_id=ctx.user.id,
                                       user_name=ctx.user.name)

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
            if not payload.user_id == int(os.getenv('ADMIN_USER_IDS')):
                return

            # Get the channel and message using the payload
            channel = self._discord_bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            chat_title = self._create_chat_title_string(user_name=str(message.author))
            await self._create_chat_thread(chat_title=chat_title,
                                           message_object=message,
                                           user_id=message.author.id,
                                           user_name=str(message.author),
                                           assistant_type="default")

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

        if not message.channel.id in list(self._active_threads.keys()):
            return

        # ignore if first character is ~
        if message.content[0] == "~":
            return

        chat = self._active_threads[message.channel.id]

        self._mongo_database.upsert(collection="chat_logs",
                                    query={"user_id": message.author.id,
                                           "thread_id": message.channel.id,
                                           "thread_title": chat.title,
                                           "start_time": chat.started_at
                                           },
                                    data={"$push": {"messages": {"human_message": message.content}}})

        logger.info(f"Sending message to the agent: {message.content}")

        try:
            response_message = await chat.thread.send("`Awaiting bot response...`")

            async with response_message.channel.typing():
                bot_response = await chat.assistant.async_process_input(input_text=message.content)

            await response_message.edit(content=bot_response)
            self._mongo_database.upsert(collection="chat_logs",
                                        query={"user_id": message.author.id,
                                               "thread_id": message.channel.id,
                                               "thread_title": chat.title,
                                               "start_time": chat.started_at},
                                        data={"$push": {"messages": {"ai_response": bot_response}}})

        except Exception as e:
            logger.error(e)

    def _create_chat_title_string(self, user_name: str) -> str:
        return f"{user_name}'s chat with {self._discord_bot.user.name}"

    async def _create_chat_thread(self,
                                  chat_title: str,
                                  message_object: discord.Message,
                                  user_id: int,
                                  user_name: str,
                                  assistant_type: str = "default"):

        thread = await message_object.create_thread(name=chat_title)

        assistant = get_assistant(assistant_type=assistant_type)
        chat = Chat(
            title=chat_title,
            owner={"id": user_id,
                   "name": user_name},
            thread=thread,
            assistant=assistant
        )

        await chat.thread.send(f"<@{user_id}> is the thread owner.")
        await chat.thread.send(f"The bot is ready to chat! "
                               f"\n(bot ignores messages starting with ~)")
        self._active_threads[chat.thread.id] = chat

    async def _make_title_card_embed(self, user_name: str, chat_title: str):
        return discord.Embed(
            title=chat_title,
            description=f"A conversation between {user_name} and the bot, started on {datetime.now()}",
            color=0x25d790,
        )
