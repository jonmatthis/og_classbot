import asyncio
from datetime import datetime

from langchain.callbacks import get_openai_callback

from chatbot.bots.workers.video_chatter_summary_builder.video_chatter_summary_builder import VideoChatterSummaryBuilder
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name, \
    VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME


async def generate_video_chatter_summaries(mongo_database: MongoDatabaseManager,
                                           thread_collection_name: str,
                                           video_chatter_summaries_collection_name: str,
                                           designated_channel_name: str = "introductions",
                                           use_anthropic: bool = False,
                                           overwrite: bool = False,
                                           ):
    thread_collection = mongo_database.get_collection(thread_collection_name)
    video_chatter_summaries_collection = mongo_database.get_collection(video_chatter_summaries_collection_name)

    student_usernames = thread_collection.distinct("_student_username")

    number_of_students = len(student_usernames)

    with get_openai_callback() as cb:
        for student_iterator, student_username in enumerate(student_usernames):

            student_threads_in_designated_channel = [thread for thread in
                                                     thread_collection.find({'_student_username': student_username,
                                                                             "channel": designated_channel_name})]

            if len(student_threads_in_designated_channel) == 0:
                print(f"-----------------------------------------------------------------------------\n"
                      f"Student - ({student_username}) has no threads in {designated_channel_name}.\n"
                      f"-----------------------------------------------------------------------------\n")
                continue

            print(f"-----------------------------------------------------------------------------\n"
                  f"Generating VideoChatter for {student_username}"
                  f"Student#{student_iterator + 1} of {number_of_students}\n"
                  f"This student has e {len(student_threads_in_designated_channel)} threads in {designated_channel_name}.\n"
                  f"-----------------------------------------------------------------------------\n")

            for thread_number, thread_entry in enumerate(student_threads_in_designated_channel):

                student_discord_username = thread_entry["_student_username"]
                student_name = thread_entry["_student_name"]

                mongo_query = {
                    "_student_name": student_name,
                    "_student_username": student_discord_username,
                    "server_name": thread_entry["server_name"],
                    "discord_user_id": thread_entry["discord_user_id"],
                    "thread_title": thread_entry["thread_title"],
                    "created_at": thread_entry["created_at"],
                    "channel": thread_entry["channel"],
                }
                mongo_database.upsert(collection=video_chatter_summaries_collection_name,
                                      query=mongo_query,
                                      data={"$set": {"threads": student_threads_in_designated_channel}})

                try:
                    video_chatter_summary_entry = video_chatter_summaries_collection.find_one(
                        {"_student_name": student_name})
                    current_video_chatter_summary = video_chatter_summary_entry.get("video_chatter_summary", "")
                    first_entry = False
                    if "video_chatter_summary" in video_chatter_summary_entry:
                        current_summary_created_at = video_chatter_summary_entry["video_chatter_summary"]["created_at"]
                        current_video_chatter_summary_created_at_datetime = datetime.strptime(
                            current_summary_created_at, '%Y-%m-%dT%H:%M:%S.%f')
                    else:
                        first_entry = True


                except Exception as e:
                    raise e

                video_chatter_summary_builder = VideoChatterSummaryBuilder(
                    current_summary=current_video_chatter_summary, )

                thread_summary = thread_entry['summary']['summary']
                thread_summary_created_at = thread_entry['summary']['created_at']
                thread_summary_created_at_datetime = datetime.strptime(thread_summary_created_at,
                                                                       '%Y-%m-%dT%H:%M:%S.%f')

                if not overwrite and not first_entry:
                    timedelta = thread_summary_created_at_datetime - current_video_chatter_summary_created_at_datetime
                    if timedelta.total_seconds() < 0:
                        print(
                            "Skipping thread because it is older than the current summary (i.e. it has already been incorporated into the summary)")
                        continue

                print(
                    f"---------Incorporating Thread#{thread_number + 1}-of-{len(student_threads_in_designated_channel)}-------------\n")
                print(f"Updating student summary based on thread with summary:\n {thread_summary}\n")

                print(f"Current student summary (before update):\n{current_video_chatter_summary}\n")

                updated_video_chatter_summary = await video_chatter_summary_builder.update_video_chatter_summary_based_on_new_conversation(
                    current_video_chatter_summary=current_video_chatter_summary,
                    new_conversation_summary=thread_summary, )

                print(f"Updated summary (after update):\n{updated_video_chatter_summary}\n\n---\n\n")
                print(f"OpenAI API callback:\n {cb}\n")

                mongo_database.upsert(collection=video_chatter_summaries_collection_name,
                                      query={"discord_username": student_username},
                                      data={"$set": {"video_chatter_summary": {"summary": updated_video_chatter_summary,
                                                                               "created_at": datetime.now().isoformat(),
                                                                               "model": video_chatter_summary_builder.llm_model}}},
                                      )
                if video_chatter_summary_entry is not None:
                    if "video_chatter_summary" in video_chatter_summary_entry:
                        mongo_database.upsert(collection=video_chatter_summaries_collection_name,
                                              query={"discord_username": student_username},
                                              data={"$push": {"previous_summaries": video_chatter_summary_entry[
                                                  "video_chatter_summary"]}}
                                              )

    mongo_database.save_json(collection_name=video_chatter_summaries_collection_name, )


if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)
    asyncio.run(generate_video_chatter_summaries(mongo_database=MongoDatabaseManager(),
                                                 thread_collection_name=thread_collection_name,
                                                 designated_channel_name="video-chatter-bot",
                                                 video_chatter_summaries_collection_name=VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME,
                                                 use_anthropic=False, ))

    # for attempt in range(10):
    #     try:
    #         print(f"Attempt #{attempt + 1}")
    #         asyncio.run(generate_video_chatter_summaries(mongo_database=MongoDatabaseManager(),
    #                                                      thread_collection_name=thread_collection_name,
    #                                                      designated_channel_name="video-chatter-bot",
    #                                                      video_chatter_summaries_collection_name=VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME,
    #                                                      use_anthropic=False, ))
    #         print(f"Successfully generated video chatter summaries for {server_name} on attempt #{attempt + 1}")
    #         break
    #     except Exception as e:
    #         print(f"Error: {e}")
    #         continue
