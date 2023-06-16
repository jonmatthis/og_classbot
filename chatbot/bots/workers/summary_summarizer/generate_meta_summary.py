import asyncio
import os
from datetime import datetime

from chatbot.bots.workers.summary_summarizer.summary_summarizer import SummarySummarizer
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from pathlib import Path
import json


async def generate_meta_summary(mongo_database: MongoDatabaseManager,
                          summaries_collection_name: str,
                          base_summary_name: str = "video_chatter"):
    summary_summarizer = SummarySummarizer()
    summaries_collection = mongo_database.get_collection(summaries_collection_name)
    all_entries = summaries_collection.find({})
    all_entries = list(all_entries)

    base_summaries = {}
    meta_summary = "[NO SUMMARY YET]"
    for entry_number, entry in enumerate(all_entries):
        student_name = entry["_student_name"]

        if student_name == "NOT_A_STUDENT":
            continue

        base_summaries[student_name] =  entry[f"{base_summary_name}_summary"]["summary"]
        print("=====================================================================================================\n")
        print(f"Updating meta summary with summary from: {student_name}\n\n")
        print(f"Student number: {entry_number + 1} of {len(all_entries)}\n\n")
        print("=====================================================================================================\n")

        # print(f"Current meta summary:\n\n{meta_summary}\n\n")

        meta_summary = await summary_summarizer.update_meta_summary_based_on_new_summary(
            current_meta_summary=meta_summary,
            new_summary=base_summaries[student_name],
        )
        mongo_database.upsert(collection_name= "video_chatter_meta_summary",
                              query={},
                              data={"$set": {"meta_summary": meta_summary},
                                    "$push": {"previous_summaries": meta_summary}})

    md_save_path = Path(
        os.getenv("PATH_TO_COURSE_DROPBOX_FOLDER")) / "course_data" / "chatbot_data" / f"{base_summary_name}_meta_summary_{datetime.now().isoformat()}.md"
    md_save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(md_save_path, 'w') as f:
        f.write(meta_summary)

    print(f"Meta summary has been successfully generated and saved at {str(md_save_path)}.")


if __name__ == '__main__':
    from chatbot.system.filenames_and_paths import VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME

    mongo_database = MongoDatabaseManager()
    asyncio.run(generate_meta_summary(mongo_database, VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME))
