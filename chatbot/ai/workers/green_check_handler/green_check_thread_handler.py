import logging
import os
import random
from pathlib import Path
from typing import Union

from dotenv import load_dotenv

from chatbot.ai.workers.green_check_handler.green_check_parser import GreenCheckMessageParser
from chatbot.ai.workers.thread_summarizer.thread_summarizer import logger
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_green_check_threads(overwrite: bool = False,
                                     save_to_json: bool = True,
                                     collection_name: str = "green_check_messages"):
    mongo_database = MongoDatabaseManager()

    collection = mongo_database.get_collection(collection_name)
    all_entries = list(collection.find())
    random.shuffle(all_entries)
    logger.info("Parsing green check messages")

    for entry in all_entries:

        print("=====================================================================================================")
        print(f"Green Check Messages for student: {entry['_student_name']}\n")
        print("=====================================================================================================")

        messages = entry["green_check_messages"]
        if len(messages) == 0:
            raise ValueError(f"Student {entry['_student_name']} has no green check messages")

        chain = GreenCheckMessageParser()
        og_parsed_output = chain.parse(input_text='\n'.join(messages))

        parsed_output = og_parsed_output.split("# Citation", 1)[-1]
        parsed_output = "# Citation" + parsed_output

        mongo_database.upsert(
            collection=collection_name,
            query={"_student_name": entry["_student_name"]},
            data={"$set": {"parsed_output": parsed_output}}
        )
        student_initials = "".join([name[0].upper() for name in entry["_student_name"].split(" ")])
        save_green_check_entry_to_markdown(base_summary_name="green_check_messages",
                                           text=parsed_output,
                                           tag=f"_{student_initials}", )

        print(f"Student: {entry['_student_name']}: \n"
              f"Messages with green check: \n{messages}\n"
              f"Parsed output: \n{parsed_output}")

    if save_to_json:
        mongo_database.save_json(collection_name=collection_name)


def save_green_check_entry_to_markdown(base_summary_name: str,
                                       text, tag: str = None,
                                       subfolder: str = None,
                                       save_path: Union[str, Path] = None, ):
    load_dotenv()
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

    print(f"Markdown file generated and saved at {str(save_path)}.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(handle_green_check_threads(collection_name="green_check_messages",
                                           overwrite=True,
                                           save_to_json=True,
                                           ))
