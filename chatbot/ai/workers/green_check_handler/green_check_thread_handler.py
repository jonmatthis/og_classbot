import logging

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

    logger.info("Parsing green check messages")

    for entry in all_entries:

        print("=====================================================================================================")
        print(f"Green Check Messages for student: {entry['_student_name']}\n")
        print("=====================================================================================================")

        messages = entry["green_check_messages"]
        if len(messages) == 0:
            raise ValueError(f"Student {entry['_student_name']} has no green check messages")

        chain = GreenCheckMessageParser()
        parsed_output =await chain.aparse(input_text = '\n'.join(messages))
        mongo_database.upsert(
            collection_name=collection_name,
            query={"_student_name": entry["_student_name"]},
            data={"$set": {"parsed_output": parsed_output}}
        )

        print(f"Student: {entry['_student_name']}: \n"
              f"Messages with green check: \n{messages}\n"
              f"Parsed output: \n{parsed_output}")

    if save_to_json:
        mongo_database.save_json(collection_name=collection_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(handle_green_check_threads(collection_name="green_check_messages",
                                           overwrite=True,
                                           save_to_json=True,
                                           ))
