from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.student_info.student_profiles.student_profile_models import StudentProfile


async def create_student_profiles_collection(thread_collection_name: str,
                                             student_profiles_collection_name: str = "student_profiles"):
    mongo_database_manager = MongoDatabaseManager()
    collection = mongo_database_manager.get_collection(collection_name=thread_collection_name)

    student_profiles = {}

    threads = await collection.find().to_list(length=None)

    for thread in threads:

        student_uuid = thread['_student_uuid']

        if student_uuid not in student_profiles:
            student_profiles[student_uuid] = StudentProfile(
                _uuid=student_uuid,
                _initials=thread['_student_initials'],
                student_info={'_student_name': thread['_student_name'],
                              '_student_username': thread['_student_username']},
                threads=[],
                total_word_count_for_all_threads={"total": 0, "student": 0, "bot": 0},
                total_character_count_for_all_threads={"total": 0, "student": 0, "bot": 0}
            )

        student_profiles[student_uuid].update(thread=thread)

        print("Adding thread to student profile - "
              f"Student: {thread['_student_initials']} - number of threads: {len(student_profiles[student_uuid].threads)}")

    # student_profiles = update_and_sort_word_count_timelines(student_profiles)

    for student_uuid, profile in student_profiles.items():
        # Use the upsert method to insert or update the student's data
        await mongo_database_manager.upsert(
            collection=student_profiles_collection_name,
            query={'_student_uuid': student_uuid},
            data=({'$set': profile.dict()})
        )
    print(f"Created {student_profiles_collection_name} collection - with {len(student_profiles)} students")


# def update_and_sort_word_count_timelines(student_profiles=Dict[StudentProfile]) -> Dict[str, List]:
#     for student_uuid, profile in student_profiles.items():
#         word_count_timelines = {}
#         count_types = ["total", "student", "bot"]
#         for type in count_types:
#             thread_timelines = [thread.word_count_cumulative[type] for thread in threads]
#             word_count_timelines[type] = thread_timelines
#
#             # Convert datetime strings to datetime objects for proper sorting
#             for thread_timeline in thread_timelines:
#                 f = 9
#             # Sort the timeline by datetime
#             thread_timeline.sort(key=lambda x: x[0])
#
#             # Convert datetime objects back to strings
#             for entry_number in range(len(thread_timeline)):
#                 thread_timeline[entry_number][0] = thread_timeline[entry_number][0].isoformat()
#
#     return word_count_timelines


if __name__ == "__main__":
    import asyncio
    from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

    server_name = "Neural Control of Real World Human Movement 2023 Summer1"

    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)

    print("Creating student profiles collection")
    asyncio.run(create_student_profiles_collection(thread_collection_name=thread_collection_name,
                                                   student_profiles_collection_name="student_profiles"))

    print("Creating anonymized student profiles collection")
    asyncio.run(create_student_profiles_collection(thread_collection_name=f"anonymized_{thread_collection_name}",
                                                   student_profiles_collection_name="anonymized_student_profiles"))

    print("Done!")
