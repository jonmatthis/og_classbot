import asyncio
import os
from pathlib import Path

from rich.console import Console

from chatbot.ai.workers.summary_summarizer.summary_summarizer import SummarySummarizer
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

console = Console()


async def generate_meta_summary(mongo_database: MongoDatabaseManager,
                                summaries_collection_name: str,
                                base_summary_name: str = "video_chatter",
                                randomize_and_rerun: bool = False,
                                overwrite: bool = False,):
    summary_summarizer = SummarySummarizer(summary_type=base_summary_name,)
    summaries_collection = mongo_database.get_collection(summaries_collection_name)
    all_student_entries = summaries_collection.find({})
    all_student_entries = list(all_student_entries)

    all_student_summaries = []
    meta_summary = "[NO SUMMARY YET]"
    flip_iterator = range(0)

    if randomize_and_rerun:
        flip_iterator = range(2)
    for flip_number in flip_iterator:
        console.rule()
        console.rule()
        console.rule("FLIP NUMBER: " + str(flip_number))
        console.rule()
        console.rule()

        if flip_number == 1:
            print("Flipping order of summaries")
            all_student_entries = list(reversed(all_student_entries))

        for student_entry_number, student_entry in enumerate(all_student_entries):
            student_name = student_entry["_student_name"]

            if student_name == "NOT_A_STUDENT":
                continue

            student_initials = "".join([name[0].upper() for name in student_name.split(" ")])

            schematized_student_summary = student_entry[f"{base_summary_name}_summary"]["summary"]
            schematized_student_summary = format_summary_output(schematized_student_summary)

            markdown_frontmatter = f"# Student: {student_initials}\n\n## Conversation summaries:\n\n"
            thread_summaries = []
            for thread in student_entry["threads"]:
                thread_summaries.append(f":{thread['thread_url']}\n\n"
                                        f"{thread['summary']['summary']}\n\n")
            thread_summaries = "\n\n".join(thread_summaries)
            to_markdown = markdown_frontmatter + thread_summaries + "\n\n" + "## Schematized student_summary\n\n" + schematized_student_summary + "\n\n"
            save_to_markdown(text=to_markdown,
                             subfolder = "student_summaries",
                             base_summary_name=base_summary_name,
                             tag=f"_{student_initials}",
                             )
            print(
                "=====================================================================================================\n")
            print(f"Updating meta summary with summary from: {student_name}\n\n")
            print(f"Student number: {student_entry_number + 1} of {len(all_student_entries)}\n\n")
            print(
                "=====================================================================================================\n")

            all_student_summaries.append(f"## Student: {student_initials}\n\n "
                                         f"Chat creation time: {student_entry['thread_creation_time']}\n"
                                         f"Threads involved: {[thread['thread_url'] for thread in student_entry['threads']]}\n\n"
                                         f"{schematized_student_summary}\n\n"
                                         f"_________________________________________________________________________\n\n")

            # print(f"Current meta summary:\n\n{meta_summary}\n\n")

            meta_summary = await summary_summarizer.update_meta_summary_based_on_new_summary(
                student_initials=student_initials,
                current_schematized_summary=meta_summary,
                new_conversation_summary=schematized_student_summary,
            )
            meta_summary = format_summary_output(meta_summary)
            mongo_database.upsert(collection_name="video_chatter_meta_summary",
                                  query={},
                                  data={"$set": {"meta_summary": meta_summary},
                                        "$push": {"previous_summaries": meta_summary}})

            print(f"Updated meta summary:\n\n{meta_summary}\n\n")

        if randomize_and_rerun:
            save_to_markdown(base_summary_name,
                             meta_summary,
                             tag=f"_flip_{flip_number}")

    save_to_markdown(base_summary_name=base_summary_name,
                     text=meta_summary,
                     tag="_meta_summary"
                     )
    save_to_markdown(text="\n\n".join(all_student_summaries),
                     base_summary_name=base_summary_name,
                     tag="_all_summaries")


def format_summary_output(schematized_student_summary):
    front_parts = ["```response-schema\n", "```schematized-summary\n"]
    back_parts = ["```", "```\n"]

    for front_part in front_parts:
        if schematized_student_summary[:len(front_part)] == front_part:
            schematized_student_summary = schematized_student_summary[len(front_part):]

    for back_part in back_parts:
        if schematized_student_summary[-len(back_part):] == back_part:
            schematized_student_summary = schematized_student_summary[:-len(back_part)]

    return schematized_student_summary


def save_to_markdown(base_summary_name: str,
                     text, tag: str = None,
                     subfolder: str = None,
                     save_path: Path = None):
    if not save_path:
        save_path = Path(
            os.getenv(
                "PATH_TO_COURSE_DROPBOX_FOLDER")) / "course_data" / "chatbot_data" / base_summary_name
    if subfolder:
        save_path = save_path / subfolder

    save_path.mkdir(parents=True, exist_ok=True)

    md_filename = f"{base_summary_name}"
    clean_file_name = md_filename.replace(":", "_").replace(".", "_")
    if tag:
        clean_file_name += tag
    clean_file_name += ".md"

    save_path = save_path / clean_file_name

    with open(str(save_path), 'w') as f:
        f.write(text)

    print(f"Meta summary has been successfully generated and saved at {str(save_path)}.")


if __name__ == '__main__':
    from chatbot.system.filenames_and_paths import VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME

    mongo_database = MongoDatabaseManager()
    asyncio.run(generate_meta_summary(mongo_database,
                                      VIDEO_CHATTER_SUMMARIES_COLLECTION_NAME,
                                      overwrite = False,
                                      randomize_and_rerun=True))
