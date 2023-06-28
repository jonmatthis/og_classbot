from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Any, Tuple, Union

from pydantic import BaseModel, Field

from chatbot.discord_bot.cogs.thread_scraper_cog.thread_stats import ThreadStats


class StudentProfile(BaseModel):
    _uuid: str
    _initials: str
    student_info: Dict[str, str] = Field(default_factory=lambda: {
        '_student_name': '', '_student_username': ''})
    threads: List[Dict] = Field(default_factory=list)
    total_word_count_for_all_threads: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    total_character_count_for_all_threads: Dict[str, int] = Field(
        default_factory=lambda: {"total": 0, "student": 0, "bot": 0})
    word_count_timelines: Dict[str, List[Dict[str,Union[datetime, int ]]]] = Field(default_factory=dict,
                                                                       description="A dictionary of lists of [datetime, cumulative_word_count] pairs for each entry in the count_types list")

    def update(self, thread: Dict[str, Any]):

        thread_stats = ThreadStats(**thread["thread_statistics"])
        self.threads.append(thread)

        # Update counts and timelines
        for count_type in ['total', 'student', 'bot']:
            self.total_word_count_for_all_threads[count_type] += thread_stats.word_count_for_this_thread[count_type]
            self.total_character_count_for_all_threads[count_type] += thread_stats.character_count_for_this_thread[
                count_type]

            if thread["_student_initials"] == "AC":
                f = 9

            if count_type not in self.word_count_timelines:
                self.word_count_timelines[count_type] = []
                last_cumulative_count = 0
            else:
                last_cumulative_count = self.word_count_timelines[count_type][-1][1]

            original_single_thread_timeline = thread_stats.word_count_cumulative[count_type]

            updated_single_thread_timeline = deepcopy(original_single_thread_timeline)

            for index, time_point in enumerate(original_single_thread_timeline):
                updated_single_thread_timeline[index] = {"message_created_at":time_point[0],
                                                         "cumulative_word_count":time_point[1] + last_cumulative_count,
                                                         "thread_id":thread["thread_id"]}

            self.word_count_timelines[count_type].extend(updated_single_thread_timeline)

            self.word_count_timelines[count_type].sort(key=lambda x: x["message_created_at"])

        f = 9
