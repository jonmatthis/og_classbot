import asyncio
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name, STUDENT_STATISTICS_COLLECTION_NAME
from chatbot.student_info.load_student_info import load_student_info


class StudentStatistics(BaseModel):
    number_of_threads: int = 0
    number_of_messages: int = 0
    total_word_count: int = 0
    threads_in_introductions: int = 0
    threads_in_literature_review: int = 0
    threads_in_video_chatter_bot: int = 0
    threads_in_bot_playground: int = 0
    total_character_count: int = 0
    student_character_count: int = 0
    total_student_word_count: int = 0


def calculate_student_statistics(student_threads):
    statistics = StudentStatistics()
    statistics.number_of_threads = len(student_threads)

    for thread in student_threads:
        statistics = _increment_channel_thread_count(statistics, thread["channel"])

        statistics.number_of_messages += thread["total_message_count"]
        statistics.total_character_count += thread["total_character_count_for_this_thread"]
        statistics.student_character_count += thread["student_character_count_for_this_thread"]
        for message in thread["messages"]:
            if message["author"] == thread["_student_username"]:
                statistics.total_student_word_count += len(message["content"].split())

    return statistics


def _increment_channel_thread_count(statistics: StudentStatistics, channel_name: str):
    if channel_name == "introductions":
        statistics.threads_in_introductions += 1
    elif channel_name == "literature-review":
        statistics.threads_in_literature_review += 1
    elif channel_name == "video-chatter-bot":
        statistics.threads_in_video_chatter_bot += 1
    elif channel_name == "bot-playground":
        statistics.threads_in_bot_playground += 1
    else:
        raise Exception(f"Unknown channel: {channel_name}")

    return statistics


async def grab_student_statistics(mongo_database: MongoDatabaseManager,
                                  thread_collection_name: str,
                                  ):
    thread_collection = mongo_database.get_collection(thread_collection_name)

    student_info = load_student_info()
    number_of_students = len(student_info)

    student_names = list(student_info.keys())

    stats_calculated_on = datetime.now().isoformat()
    all_student_statistics = {}
    for student_number, student_name in enumerate(student_names):
        student_username = student_info[student_name]["discord_username"]
        print(f"-----------------------------------------------------------------------------\n"
              f"Generating statistics for {student_name} ({student_username})\n"
              f"Student#{student_number + 1} of {number_of_students}\n"
              f"-----------------------------------------------------------------------------\n")

        student_threads = [thread for thread in
                           thread_collection.find({'_student_name': student_name})]

        one_student_statistics = calculate_student_statistics(student_threads)
        student_dict = one_student_statistics.dict(exclude={"_id", "stats_calculation_time"})
        student_dict["discord_username"] = student_info[student_name]["discord_username"]
        all_student_statistics[student_name] = student_dict


        if all_student_statistics[student_name]["total_student_word_count"] == 0:
            print(f"WARNING: {student_name} has no student messages")
        mongo_database.upsert(collection_name=STUDENT_STATISTICS_COLLECTION_NAME,
                              query={"stats_calculation_time": stats_calculated_on},
                              data={"$set": {student_name: one_student_statistics.dict()}})

    mongo_database.save_json(collection_name=STUDENT_STATISTICS_COLLECTION_NAME, )

    df = pd.DataFrame.from_dict(all_student_statistics).T
    df.to_csv(str(Path(os.getenv("PATH_TO_COURSE_DROPBOX_FOLDER")) / f"student_stats_{datetime.now().isoformat()}.csv"))


if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)
    asyncio.run(grab_student_statistics(mongo_database=MongoDatabaseManager(),
                                        thread_collection_name=thread_collection_name,
                                        ))
