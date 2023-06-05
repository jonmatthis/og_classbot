from datetime import datetime

from chatbot.bots.workers.thread_summarizer.thread_summarizer import logger, ThreadSummarizer
from chatbot.bots.workers.thread_summarizer.split_thread_data_into_chunks import split_thread_data_into_chunks
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name


async def summarize_threads(server_name: str,
                            collection_name: str = None,
                            overwrite: bool = False,
                            save_to_json: bool = True):
    mongo_database = MongoDatabaseManager()
    if collection_name is None:
        collection_name = get_thread_backups_collection_name(server_name=server_name)

    thread_collection = mongo_database.get_collection(collection_name)
    logger.info("Generating thread summary")
    total_cost = 0
    for thread_entry in thread_collection.find():

        if "summary" in thread_entry and not overwrite:
            logger.info(f"Thread summary already exists, skipping thread: {thread_entry['_id']}")
            continue

        thread_chunks = split_thread_data_into_chunks(messages=thread_entry["messages"])

        try:
            thread_summarizer = ThreadSummarizer(use_anthropic=True)
            thread_summary = await thread_summarizer.summarize(thread_chunks=thread_chunks)
        except Exception as e:
            logger.error(f"Summary generation failed with error: {e}. Trying again with OpenAI API")
            thread_summarizer = ThreadSummarizer(use_anthropic=False)
            thread_summary = await thread_summarizer.summarize(thread_chunks=thread_chunks)

        logger.info(f"Saving thread summary to mongo database, summary: {thread_summary}")
        thread_cost = 0
        for chunk in thread_chunks:
            thread_cost += chunk["token_count"] * thread_summarizer.dollars_per_token
        total_cost += thread_cost

        mongo_database.upsert(
            collection=get_thread_backups_collection_name(server_name=server_name),
            query={"_id": thread_entry["_id"]},
            data={
                "$set": {
                    "summary": {"summary": thread_summary["output_text"],
                                "intermediate_steps": thread_summary["intermediate_steps"],
                                "thread_chunks": thread_chunks,
                                "cost": thread_cost,
                                "model": thread_summarizer.llm_model,
                                "created_at": datetime.now().isoformat(),
                                "date": datetime.now().isoformat()}
                }
            }
        )
        print(f"Thread summary: {thread_summary['output_text']}\n"
              f"Thread summary cost: ${thread_cost:.5f}\n"
              f"Total cost (so far): ${total_cost:.5f}\n"
              f"----------------------------\n")



    print(f"Done summarizing threads!\n\n Total estimated cost (final): ${total_cost:.2f}\n\n")
    if save_to_json:
        mongo_database.save_json(collection_name=collection_name)
if __name__ == "__main__":
    import asyncio

    asyncio.run(summarize_threads(server_name="Neural Control of Real World Human Movement 2023 Summer1",
                                  overwrite=False,
                                  save_to_json=True))
