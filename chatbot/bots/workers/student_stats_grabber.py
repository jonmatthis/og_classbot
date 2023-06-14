import asyncio
from datetime import datetime

from langchain.callbacks import get_openai_callback

from chatbot.bots.workers.student_summary_builder.student_summary_builder import StudentSummaryBuilder
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name, STUDENT_SUMMARIES_COLLECTION_NAME
from chatbot.system.get_external_info import load_student_info


def calculate_student_statistics(student_threads):
    statistics = {"num_threads": 0, "num_messages": 0, "total_word_count": 0}
    statistics["num_threads"] = len(student_threads)

    for thread in student_threads:
        statistics["num_messages"] += len(thread["messages"])
        for message in thread["messages"]:
            statistics["total_word_count"] += len(message["message"].split())

    return statistics


async def grab_student_statistics(mongo_database: MongoDatabaseManager,
                                  thread_collection_name: str,
                                  student_summaries_collection_name: str,
                                  student_statistics_collection_name: str,
                                  overwrite: bool = False,
                                  ):
    thread_collection = mongo_database.get_collection(thread_collection_name)
    student_summaries_collection = mongo_database.get_collection(student_summaries_collection_name)
    student_statistics_collection = mongo_database.get_collection(student_statistics_collection_name)

    student_usernames = thread_collection.distinct("thread_owner_name")

    number_of_students = len(student_usernames)

    student_info = load_student_info()

    student_names  = list(student_info.keys())

    for student_number, student_name in enumerate(student_names):
        student_username = student_info[student_name]["discord_username"]
        print(f"-----------------------------------------------------------------------------\n"
              f"Generating statistics for {student_name} ({student_username})\n"
              f"Student#{student_number + 1} of {number_of_students}\n"
              f"-----------------------------------------------------------------------------\n")

        student_threads = [thread for thread in
                           thread_collection.find({'thread_owner_name': student_username})]

        student_statistics = calculate_student_statistics(student_threads)

        mongo_database.upsert(collection=student_statistics_collection,
                              query={"discord_username": student_username},
                              data={"$set": {"threads": student_threads,
                                             "statistics": student_statistics}})

        try:
            student_summary_entry = student_summaries_collection.find_one(
                {"discord_username": student_username})
            current_student_summary = student_summary_entry.get("student_summary", "")
            if not current_student_summary == "":
                current_student_summary = current_student_summary.get("summary", "")
                current_summary_created_at = student_summary_entry["student_summary"]["created_at"]
                current_student_summary_created_at_datetime = datetime.strptime(current_summary_created_at,
                                                                                '%Y-%m-%dT%H:%M:%S.%f')

        except Exception as e:
            print(f"Error: {e}")
            current_student_summary = "You have not seen this student before..."

        student_summary_builder = StudentSummaryBuilder(current_summary=current_student_summary, )

        for thread_number, thread in enumerate(student_threads):
            thread_summary = thread['summary']['summary']
            thread_summary_created_at = thread['summary']['created_at']
            thread_summary_created_at_datetime = datetime.strptime(thread_summary_created_at,
                                                                   '%Y-%m-%dT%H:%M:%S.%f')

            if not overwrite:
                timedelta = thread_summary_created_at_datetime - current_student_summary_created_at_datetime
                if timedelta.total_seconds() < 0:
                    print(
                        "Skipping thread because it is older than the current summary (i.e. it has already been incorporated into the summary)")
                    continue

            print(f"---------Incorporating Thread#{thread_number + 1}-of-{len(student_threads)}-------------\n")
            print(f"Updating student summary based on thread with summary:\n {thread_summary}\n")

            print(f"Current student summary (before update):\n{current_student_summary}\n")

            updated_student_summary = await student_summary_builder.update_student_summary_based_on_new_conversation(
                current_student_summary=current_student_summary,
                new_conversation_summary=thread_summary, )

            print(f"Updated summary (after update):\n{updated_student_summary}\n\n---\n\n")
            print(f"OpenAI API callback:\n {cb}\n")

            mongo_database.upsert(collection=student_summaries_collection_name,
                                  query={"discord_username": student_username},
                                  data={"$set": {"student_summary": {"summary": updated_student_summary,
                                                                     "created_at": datetime.now().isoformat(),
                                                                     "model": student_summary_builder.llm_model}}},
                                  )
            if student_summary_entry is not None:
                if "student_summary" in student_summary_entry:
                    mongo_database.upsert(collection=student_summaries_collection_name,
                                          query={"discord_username": student_username},
                                          data={"$push": {"previous_summaries": student_summary_entry[
                                              "student_summary"]}}
                                          )

    mongo_database.save_json(collection_name=student_summaries_collection_name, )


if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)
    for attempt in range(10):
        try:
            asyncio.run(grab_student_statistics(mongo_database=MongoDatabaseManager(),
                                                thread_collection_name=thread_collection_name,
                                                student_summaries_collection_name=STUDENT_SUMMARIES_COLLECTION_NAME,
                                                student_statistics_collection_name="student_statistics",
                                                ))
        except Exception as e:
            print(f"Error: {e}")
            continue
