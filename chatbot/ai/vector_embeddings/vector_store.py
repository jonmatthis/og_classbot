import os
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from langchain import OpenAI
from langchain.agents import create_vectorstore_agent
from langchain.agents.agent_toolkits import VectorStoreInfo, VectorStoreToolkit
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.schema import Document
from langchain.vectorstores import Chroma
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

    documents = paper_summaries_to_documents(all_entries)

    embeddings = OpenAIEmbeddings()
    chroma_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(Path(os.getenv("PATH_TO_CHROMA_PERSISTENCE_FOLDER"))/collection_name),
    )

    vectorstore_info = VectorStoreInfo(
        name=collection_name,
        description="Vector store of embeddings of paper summaries",
        vectorstore=chroma_store,
    )
    toolkit = VectorStoreToolkit(vectorstore_info=vectorstore_info)
    agent_executor = create_vectorstore_agent(llm=OpenAI(),
                                              toolkit=toolkit,
                                              verbose=True)

    agent_executor.run("Tell me about the neural control human movement")
    f=9

def paper_summaries_to_documents(all_entries):
    documents = []
    for entry in all_entries:
        documents.append(Document(page_content=entry["parsed_output_string"],
                                  metadata={"_student_uuid": entry["_student_uuid"],
                                            "thread_url": entry["thread_url"],
                                            "source": entry["parsed_output_dict"]["citation"],
                                            **entry["parsed_output_dict"], }))
    return documents


if __name__ == "__main__":
    import asyncio

    asyncio.run(create_vector_store(collection_name="green_check_messages",
                                    query={"parsed_output_dict": {"$exists": True}},
                                    save_to_json=True,
                                    ))
