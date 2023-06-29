from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Any, Tuple

from pydantic import BaseModel, Field

from chatbot.discord_bot.cogs.thread_scraper_cog.thread_stats import ThreadStats


class StudentProfile(BaseModel):
    uuid: str
    initials: str
    student_info: Dict[str, str] = Field(default_factory=lambda: {
        '_student_name': '', '_student_username': ''})
    threads: List[Dict] = Field(default_factory=list)
    total_message_count_for_all_threads: Dict[str, int] = Field(default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    total_word_count_for_all_threads: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    total_character_count_for_all_threads: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    word_count_by_datetimes_by_type: Dict[str, List[Tuple[datetime, int]]] = Field(
        default_factory=lambda: {"total": [], "student": [], "bot": []})
    cumulative_word_count_by_datetimes_by_type: Dict[str, List[Tuple[datetime, int]]] = Field(default_factory=lambda: {"total": [], "student": [], "bot": []})
    def update(self, thread: Dict[str, Any]):

        thread_stats = ThreadStats(**thread["thread_statistics"])
        self.threads.append(thread)


        # Update total word and character counts
        for count_type in ["total", "student", "bot"]:
            self.total_message_count_for_all_threads[count_type] += thread_stats.message_count_for_this_thread[count_type]
            self.total_word_count_for_all_threads[count_type] += thread_stats.word_count_for_this_thread[count_type]
            self.total_character_count_for_all_threads[count_type] += thread_stats.character_count_for_this_thread[count_type]

        # Update word count by datetimes
        for count_type, all_wordcount_by_datetimes in self.word_count_by_datetimes_by_type.items():
            all_wordcount_by_datetimes.extend(deepcopy(thread_stats.wordcount_by_datetimes_by_type[count_type]))
            self.word_count_by_datetimes_by_type[count_type] = sorted(all_wordcount_by_datetimes)