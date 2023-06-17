import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name, STUDENT_STATISTICS_COLLECTION_NAME, \
    clean_path_string
from chatbot.student_info.load_student_info import load_student_info

load_dotenv()
class ClassStatistics(BaseModel):
    number_of_students: int = 0
    number_of_threads: int = 0
    word_count_total: int = 0
    word_count_students: int = 0
    message_count_total: int = 0
    message_count_students: int = 0
    character_count_total: int = 0
    character_count_students: int = 0

    average_words_per_thread: float = 0
    average_words_per_student: float = 0
    average_messages_per_thread: float = 0
    average_messages_per_student: float = 0
    average_characters_per_thread: float = 0
    average_characters_per_student: float = 0


class StudentStatistics(BaseModel):
    number_of_threads: int = 0
    number_of_messages_total: int = 0
    number_of_messages_student: int = 0
    character_count_total: int = 0
    character_count_student: int = 0
    word_count_total: int = 0
    word_count_student: int = 0

    average_words_per_thread_total: float = 0
    average_words_per_thread_student: float = 0

    threads_in_introductions: int = 0
    threads_in_literature_review: int = 0
    threads_in_video_chatter_bot: int = 0
    threads_in_bot_playground: int = 0


def calculate_student_statistics(student_threads):
    statistics = StudentStatistics()
    statistics.number_of_threads = len(student_threads)

    for thread in student_threads:
        statistics = _increment_channel_thread_count(statistics, thread["channel"])

        statistics.number_of_messages_total += len(thread["messages"])
        for message in thread["messages"]:
            message_word_count = len(message["content"].split())
            messsage_character_count = len(message["content"])

            statistics.character_count_total += len(message["content"])
            statistics.word_count_total += len(message["content"].split())

            if not message["author_id"] == int(os.getenv("DISCORD_BOT_ID")):
                statistics.number_of_messages_student += 1
                statistics.character_count_student += messsage_character_count
                statistics.word_count_student += message_word_count
    if statistics.number_of_threads > 0:
        statistics.average_words_per_thread_total = statistics.word_count_total // statistics.number_of_threads
        statistics.average_words_per_thread_student = statistics.word_count_student // statistics.number_of_threads
    return statistics


def calculate_class_statistics(all_student_statistics: Dict[str, StudentStatistics]):
    class_statistics = ClassStatistics()
    class_statistics.number_of_students = len(all_student_statistics)

    for student_name, student_stats in all_student_statistics.items():
        class_statistics.word_count_total += student_stats.word_count_total
        class_statistics.word_count_students += student_stats.word_count_student
        class_statistics.message_count_total += student_stats.number_of_messages_total
        class_statistics.message_count_students += student_stats.number_of_messages_student
        class_statistics.character_count_total += student_stats.character_count_total
        class_statistics.character_count_students += student_stats.character_count_student

    if class_statistics.number_of_students > 0:
        class_statistics.average_words_per_student = class_statistics.word_count_students // class_statistics.number_of_students
        class_statistics.average_messages_per_student = class_statistics.message_count_students // class_statistics.number_of_students
        class_statistics.average_characters_per_student = class_statistics.character_count_students // class_statistics.number_of_students

    if class_statistics.number_of_threads > 0:
        class_statistics.average_words_per_thread = class_statistics.word_count_total // class_statistics.number_of_threads
        class_statistics.average_messages_per_thread = class_statistics.message_count_total // class_statistics.number_of_threads
        class_statistics.average_characters_per_thread = class_statistics.character_count_total // class_statistics.number_of_threads

    return class_statistics



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

    stats_calculated_on = datetime.now().date()
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
        all_student_statistics[student_name] = one_student_statistics

        if all_student_statistics[student_name].word_count_student == 0:
            print(f"WARNING: {student_name} has no student messages")
        mongo_database.upsert(collection_name=STUDENT_STATISTICS_COLLECTION_NAME,
                              query={"student_name": student_name},
                              data={"$set":  one_student_statistics.dict()})

    # Calculate class statistics and save to DB or file
    class_stats = calculate_class_statistics(all_student_statistics)
    mongo_database.upsert(collection_name=STUDENT_STATISTICS_COLLECTION_NAME,
                          query={"student_name": "class_statistics"},
                          data={"$set": class_stats.dict()})

    mongo_database.save_json(collection_name=STUDENT_STATISTICS_COLLECTION_NAME)


    save_to_csv(all_student_statistics)


def save_to_csv(all_student_statistics):
    all_stats = {key: value.dict() for key, value in all_student_statistics.items()}
    df = pd.DataFrame.from_dict(all_stats).T
    file_name = f"student_stats_{datetime.now().isoformat()}"
    file_name = clean_path_string(file_name)
    file_name += ".csv"
    save_path = Path(os.getenv("PATH_TO_COURSE_DROPBOX_FOLDER")) / "course_data" / "student_info" / file_name
    save_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(str(save_path))


if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)
    asyncio.run(grab_student_statistics(mongo_database=MongoDatabaseManager(),
                                        thread_collection_name=thread_collection_name,
                                        ))
