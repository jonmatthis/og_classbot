from datetime import datetime
from typing import List, Dict

from chatbot.student_info.find_student_name import get_initials
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager


async def create_student_profiles_collection( thread_collection_name:str,
                                              student_profiles_collection_name:str = "student_profiles"):

    mongo_database_manager = MongoDatabaseManager()
    collection = mongo_database_manager.get_collection(collection_name=thread_collection_name)

    student_data = {}

    threads = await collection.find().to_list(length=None)

    for thread in threads:
        student_uuid = thread['_student_uuid']
        if student_uuid not in student_data:

            student_data[student_uuid] = {
                "_uuid": student_uuid,
                "_initials": thread['_student_initials'],
                "student_info": {
                    '_student_name': thread['_student_name'],
                    '_student_username': thread['_student_username'],
                    },
                'threads': [],
            }

        student_data[student_uuid]['threads'].append(thread)
        print(f"Student: {thread['_student_initials']} - number of threads: {len(student_data[student_uuid]['threads'])}")

    for student_uuid, data in student_data.items():
        data['word_count_timeline'] = update_and_sort_word_count_timeline(data['threads'])

    for student_uuid, data in student_data.items():
        # Use the upsert method to insert or update the student's data
        await mongo_database_manager.upsert(
            collection=student_profiles_collection_name,
            query={'_student_uuid': student_uuid},
            data=({'$set': data})
        )
    print(f"Created {student_profiles_collection_name} collection - with {len(student_data)} students")


def update_and_sort_word_count_timeline(threads: List[Dict]) -> List[List]:
    word_count_timelines = {}
    word_count_timelines["total"] = [thread['cumulative_word_count_total'] for thread in threads]
    word_count_timelines["student"] = [thread['cumulative_word_count_student'] for thread in threads]


    # Flatten the list of lists
    word_count_timelines = [item for sublist in word_count_timelines for item in sublist]

    # Convert datetime strings to datetime objects for proper sorting
    for i in range(len(word_count_timelines)):
        word_count_timelines[i][0] = datetime.fromisoformat(word_count_timelines[i][0].replace('Z', '+00:00'))

    # Sort the timeline by datetime
    word_count_timelines.sort(key=lambda x: x[0])

    # Convert datetime objects back to strings
    for i in range(len(word_count_timelines)):
        word_count_timelines[i][0] = word_count_timelines[i][0].isoformat()

    return word_count_timelines


if __name__ == "__main__":
    import asyncio
    from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

    server_name ="Neural Control of Real World Human Movement 2023 Summer1"

    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)

    print("Creating student profiles collection")
    asyncio.run(create_student_profiles_collection(thread_collection_name =thread_collection_name,
                                                   student_profiles_collection_name="student_profiles"))

    print("Creating anonymized student profiles collection")
    asyncio.run(create_student_profiles_collection(thread_collection_name=f"anonymized_{thread_collection_name}",
                                                   student_profiles_collection_name="anonymized_student_profiles"))

    print("Done!")