import logging
from datetime import datetime

import discord

from chatbot.langchain_stuff.llm_chain.course_assistant_llm_chain import CourseAssistant

logger = logging.getLogger(__name__)

class ChatCog(discord.Cog):
    def __init__(self, discord_bot: discord.Bot):
        self._discord_bot = discord_bot
        self._active_chats = {}
        self._course_assistant_llm_chain = CourseAssistant()

    @discord.slash_command(name="chat", description="Chat with the bot")
    async def chat(self,
                   ctx: discord.ApplicationContext):

        chat_title = f"{ctx.user.name}'s chat with {self._discord_bot.user.name}"
        logger.info(f"Starting chat: {chat_title}")



        message_embed = discord.Embed(
            title=chat_title,
            description=f"A conversation between {ctx.user.name} and the bot, started on {datetime.now()}",
            color=0x25d790,
        )

        message_thread = await ctx.send(embed=message_embed)


        self._active_chats["thread"] = await message_thread.create_thread(
            name=chat_title,
        )

        self._active_chats["owner"] = ctx.user.id
        self._active_chats["title"] = chat_title

        await ctx.respond("Conversation started.")
        await self._active_chats["thread"].send(f"<@{str(ctx.user.id)}> is the thread owner.")
        await self._active_chats["thread"].send(f"`The bot is ready to chat! "
                                                f"\n(bot ignores messages starting with ~)")

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        logger.info(f"Received message: {message.content}")

        # Make sure we won't be replying to ourselves.
        if message.author.id == self._discord_bot.user.id:
            return

        # Make sure we're only replying to the active chat. (TODO - allow multiple inputs at the same time)
        if not message.channel.id == self._active_chats["thread"].id:
            return

        # ignore if first character is ~
        if message.content[0] == "~":
            return

        logger.info(f"Sending message to the agent: {message.content}")

        response_message = await self._active_chats["thread"].send("`Awaiting bot response...`")


        async with response_message.channel.typing():
            bot_response = self._course_assistant_llm_chain.chain.run(human_input=message.content)

        await response_message.edit(content=bot_response)

