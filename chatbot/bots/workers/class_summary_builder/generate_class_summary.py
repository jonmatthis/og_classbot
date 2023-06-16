import asyncio
import uuid
from copy import deepcopy
from datetime import datetime

from langchain.callbacks import get_openai_callback

from chatbot.bots.workers.class_summary_builder.class_summary_builder import ClassSummaryBuilder
from chatbot.bots.workers.student_summary_builder.student_summary_builder import time_since_last_summary, \
    StudentSummaryBuilder
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name, CLASS_SUMMARY_COLLECTION_NAME, \
    STUDENT_SUMMARIES_COLLECTION_NAME


async def generate_class_summary(mongo_database: MongoDatabaseManager,
                                 student_summary_collection_name: str,
                                 class_summary_collection_name: str,
                                 use_anthropic: bool = False,
                                 overwrite: bool = False,
                                 ):

    student_summary_collection = mongo_database.get_collection(student_summary_collection_name)
    class_summary_collection = mongo_database.get_collection(class_summary_collection_name)

    student_usernames = student_summary_collection.distinct("discord_username")

    number_of_students = len(student_usernames)

    class_summary_id = str(uuid.uuid4())

    class_summary_builder = ClassSummaryBuilder()
    current_class_summary = "This is the first student you are incorporating into the class summary."


    for student_number, student_username in enumerate(student_usernames):
        try:
            print(f"-----------------------------------------------------------------------------\n"
                  f"Incorporating summary for {student_username} into course summary\n"
                  f"Student#{student_number + 1} of {number_of_students}\n"
                  f"-----------------------------------------------------------------------------\n")

            if student_username in ["Jon#8343", "ProfJon#4002"]:
                print("Skip the Prof lol")
                continue


            try:
                student_summary_entry = student_summary_collection.find_one(
                    {"discord_username": student_username})
                current_student_summary = student_summary_entry["student_summary"]

                current_summary_created_at = student_summary_entry["student_summary"]["created_at"]
                current_student_summary_created_at_datetime = datetime.strptime(current_summary_created_at, '%Y-%m-%dT%H:%M:%S.%f')
            except Exception as e:
                raise (f"Error: {e} - I haven't seen this student before!")



            print(f"Current student summary (before update):\n{current_student_summary}\n")

            updated_class_summary = await class_summary_builder.update_class_summary_based_on_new_student_summary(
                current_class_summary=current_class_summary,
                new_student_summary=current_student_summary, )

            print(f"Updated summary (after update):\n{updated_class_summary}\n\n---\n\n")
            current_class_summary = deepcopy(updated_class_summary)

            mongo_database.upsert(collection_name=class_summary_collection_name,
                                  query={"summary_id": class_summary_id},
                                  data={"$set": {"summary": updated_class_summary,
                                                 "created_at": datetime.now().isoformat(),
                                                 "model": class_summary_builder.llm_model},
                                        "$push": {"student_summaries": student_summary_entry,
                                                  "interim_summaries": current_class_summary},
                                        "$addToSet": {"student_usernames": student_username}
                                        }
                                  )
        except Exception as e:
            print(f"Error: {e}")
            raise(e)

    mongo_database.save_json(collection_name=class_summary_collection_name, )

if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"

    for attempt in range(10):
        try:
            asyncio.run(generate_class_summary(mongo_database=MongoDatabaseManager(),
                                               student_summary_collection_name=STUDENT_SUMMARIES_COLLECTION_NAME,
                                               class_summary_collection_name=CLASS_SUMMARY_COLLECTION_NAME,
                                               use_anthropic=False, ))
        except Exception as e:
            print(f"Error: {e}")
            continue
