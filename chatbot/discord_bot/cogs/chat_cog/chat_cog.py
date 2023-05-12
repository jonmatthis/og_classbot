import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

import discord
from pydantic import BaseModel

from chatbot.langchain_stuff.llm_chain.course_assistant_llm_chain import CourseAssistant

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


class ChatCog(discord.Cog):
    def __init__(self, discord_bot: discord.Bot):
        self._discord_bot = discord_bot
        self._active_threads = {}
        # self._course_assistant_llm_chain = CourseAssistant()
        self._course_assistant_llm_chains = {}

    @discord.slash_command(name="chat", description="Chat with the bot")
    async def chat(self,
                   ctx: discord.ApplicationContext):

        chat_title = f"{ctx.user.name}'s chat with {self._discord_bot.user.name}"

        logger.info(f"Starting chat {chat_title}")

        title_card_embed = await self._make_title_card_embed(ctx, chat_title)
        message_object = await ctx.send(embed=title_card_embed)

        await self._create_chat_thread(chat_title=chat_title,
                                       message_object=message_object,
                                       user=ctx.user)

    async def _create_chat_thread(self,
                                  chat_title: str,
                                  message_object: discord.Message,
                                  user: discord.User):
        thread = await message_object.create_thread(name=chat_title)
        chat = Chat(
            title=chat_title,
            owner={"id": user.id,
                   "name": user.name},
            thread=thread,
            assistant=CourseAssistant()
        )

        await chat.thread.send(f"<@{str(user.id)}> is the thread owner.")
        await chat.thread.send(f"The bot is ready to chat! "
                               f"\n(bot ignores messages starting with ~)")
        self._active_threads[chat.thread.id] = chat

    async def _make_title_card_embed(self, ctx, chat_title: str):
        return discord.Embed(
            title=chat_title,
            description=f"A conversation between {ctx.user.name} and the bot, started on {datetime.now()}",
            color=0x25d790,
        )

    @discord.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        logger.info(f"Received reaction: {payload}")
        if not payload.user_id == int(os.getenv('ADMIN_USER_IDS')):
            return

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        logger.info(f"Received message: {message.content}")

        # Make sure we won't be replying to ourselves.
        if message.author.id == self._discord_bot.user.id:
            return

        # Only respond to non-thread messages in the active channel
        if not message.channel.__class__ == discord.Thread:
            return

        if not message.channel.id in list(self._active_threads.keys()):
            return

        # ignore if first character is ~
        if message.content[0] == "~":
            return

        logger.info(f"Sending message to the agent: {message.content}")
        chat = self._active_threads[message.channel.id]
        try:
            response_message = await chat.thread.send("`Awaiting bot response...`")

            async with response_message.channel.typing():
                bot_response = chat.assistant.process_input(input_text=message.content)

            await response_message.edit(content=bot_response)
        except Exception as e:
            logger.error(e)
