from typing import List, Dict, Tuple

from discord import Message
from pydantic import BaseModel, Field


class ThreadStats(BaseModel):
    bot_id: int
    green_check_emoji_present: bool = False
    thread_as_list_of_strings: List[str] = Field(default_factory=list)
    word_count_for_this_thread: Dict[str, int] = Field(default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    character_count_for_this_thread: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    word_count_cumulative: Dict[str, List[Tuple[str, int]]] = Field(
        default_factory=lambda: {"total": [], "student": [], "bot": []})
    thread_as_one_string: str = Field(default="")

    class Config:
        orm_mode = True

    def update(self, message: Message):
        is_bot_user = message.author.id == self.bot_id
        message_author_str = str(message.author)

        message_content = message.content
        if message_content == '':
            return

        green_check_emoji_present_in_message = self.determine_if_green_check_present(message)
        if green_check_emoji_present_in_message:
            self.green_check_emoji_present = True

        self.thread_as_list_of_strings.append(f"{message_author_str} said: '{message_content}'")
        self.thread_as_one_string = "\n".join(self.thread_as_list_of_strings)

        message_word_count = len(message_content.split(' '))
        message_character_count = len(message_content)

        self.word_count_for_this_thread["total"] += message_word_count
        self.character_count_for_this_thread["total"] += message_character_count
        self.word_count_cumulative["total"].append(
            (message.created_at.isoformat(), self.word_count_for_this_thread["total"]))

        if not is_bot_user:
            self.word_count_for_this_thread["student"] += message_word_count
            self.character_count_for_this_thread["student"] += message_character_count
            self.word_count_cumulative["student"].append(
                (message.created_at.isoformat(), self.word_count_for_this_thread["student"]))
        else:
            self.word_count_for_this_thread["bot"] += message_word_count
            self.character_count_for_this_thread["bot"] += message_character_count
            self.word_count_cumulative["bot"].append(
                (message.created_at.isoformat(), self.word_count_for_this_thread["bot"]))

    def determine_if_green_check_present(self, message: Message) -> bool:
        reactions = message.reactions
        green_check_emoji_present = False

        if len(reactions) > 0:
            for reaction in reactions:
                if reaction.emoji == '✅':
                    green_check_emoji_present = True
                    break

        if "Successfully sent summary" in message.content:
            green_check_emoji_present = False

        return green_check_emoji_present
