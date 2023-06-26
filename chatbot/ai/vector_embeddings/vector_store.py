import os
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from langchain.indexes import VectorstoreIndexCreator
from langchain.schema import Document
from rich import print

from chatbot.ai.workers.thread_summarizer.thread_summarizer import logger
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager


async def create_vector_store(save_to_json: bool = True,
                              collection_name: str = "green_check_messages",
                              query: dict = defaultdict()):
    mongo_database = MongoDatabaseManager()

    collection = mongo_database.get_collection(collection_name)
    all_entries = await collection.find(query).to_list(length=None)

    random.shuffle(all_entries)
    logger.info("Creating vector store from {collection_name} collection with {len(all_entries)} entries")

    documents = []
    for entry in all_entries:
        documents.append(Document(page_content=entry["parsed_output_string"],
                                  metadata={"_student_uuid": entry["_student_uuid"],
                                            "thread_url": entry["thread_url"],
                                            "source": entry["parsed_output_dict"]["citation"],
                                            **entry["parsed_output_dict"], }))

    index = VectorstoreIndexCreator().from_documents(documents=documents)

    response = index.query_with_sources(
        "Tell me about the role of eye movements in the neural control of human movement", )

    print(response)
    f = 9

if __name__ == "__main__":
    import asyncio

    asyncio.run(create_vector_store(collection_name="green_check_messages",
                                    query={"parsed_output_dict": {"$exists": True}},
                                    save_to_json=True,
                                    ))
