from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.student_info.student_profiles.plots.plot_student_profiles import plot_word_count_timelines
from chatbot.student_info.student_profiles.student_profile_models import StudentProfile


async def create_student_profiles_collection(thread_collection_name: str,
                                             student_profiles_collection_name: str = "student_profiles",
                                             show_plots: bool = False,):
    mongo_database_manager = MongoDatabaseManager()
    collection = mongo_database_manager.get_collection(collection_name=thread_collection_name)

    student_profiles = {}

    threads = await collection.find().to_list(length=None)

    for thread in threads:

        student_uuid = thread['_student_uuid']

        if student_uuid not in student_profiles:
            student_profiles[student_uuid] = StudentProfile(
                uuid=student_uuid,
                initials=thread['_student_initials'],
                student_info={'_student_name': thread['_student_name'],
                              '_student_username': thread['_student_username']},
            )

        student_profiles[student_uuid].update(thread=thread)

        print("Adding thread to student profile - "
              f"Student: {thread['_student_initials']} - number of threads: {len(student_profiles[student_uuid].threads)}")

    # student_profiles = update_and_sort_word_count_timelines(student_profiles)

    cumulative_word_count_by_student = {}
    for student_uuid, profile in student_profiles.items():


        for count_type, word_count_by_datetimes in profile.word_count_by_datetimes_by_type.items():
            profile.cumulative_word_count_by_datetimes_by_type[count_type] = []
            cumulative_word_count = 0
            for datetime, word_count in word_count_by_datetimes:
                cumulative_word_count += word_count
                profile.cumulative_word_count_by_datetimes_by_type[count_type].append((datetime, cumulative_word_count))
        cumulative_word_count_by_student[profile.initials] = profile.cumulative_word_count_by_datetimes_by_type

        # Use the upsert method to insert or update the student's data
        await mongo_database_manager.upsert(
            collection=student_profiles_collection_name,
            query={'_student_uuid': student_uuid},
            data={'$set': profile.dict()}
        )
    if show_plots:
        plot_word_count_timelines(student_profiles)
        print(f"Created {student_profiles_collection_name} collection - with {len(student_profiles)} students")






if __name__ == "__main__":
    import asyncio
    from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

    server_name = "Neural Control of Real World Human Movement 2023 Summer1"

    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)

    print("Creating student profiles collection")
    asyncio.run(create_student_profiles_collection(thread_collection_name=thread_collection_name,
                                                   student_profiles_collection_name="student_profiles",
                                                   show_plots=True))

    # print("Creating anonymized student profiles collection")
    # asyncio.run(create_student_profiles_collection(thread_collection_name=f"anonymized_{thread_collection_name}",
    #                                                student_profiles_collection_name="anonymized_student_profiles"))

    print("Done!")
