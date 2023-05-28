import logging
from typing import List

from langchain import OpenAI, PromptTemplate, LLMChain

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

logger = logging.getLogger(__name__)
class ThreadSummarizer:
    def __init__(self,
                 thread_data: List[str]):
        self.thread_as_string = "\n".join(str(message) for message in thread_data)

        prompt = PromptTemplate(
            template="Provide an detailed summary of the following thread."
                     "(NOTE - Keep in mind that sometimes a conversation will involve a student trying to poke at the boundaries of the AI models's knowledge and security. In this case, we consider that as evidence of interest in AI and Large Language Models(llms)!"
                     ":\n\n{thread}"
                     "\n\nSUMMARY:",
            input_variables=["thread"])

        self.chain = LLMChain(llm=OpenAI(temperature=0),
                              prompt=prompt,
                              verbose=True)

    async def summarize(self) -> str:
        return await self.chain.arun(self.thread_as_string)

if __name__ == "__main__":

    mongo_database = MongoDatabaseManager()
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection = mongo_database.get_collection(get_thread_backups_collection_name(server_name=server_name))
    logger.info("Generating thread summary")

    # thread_summary = await ThreadSummarizer(thread_as_list_of_strings).summarize()
    # logger.info(f"Saving thread summary to mongo database, summary: {thread_summary}")
    # self.mongo_database.upsert(
    #     collection=get_thread_backups_collection_name(server_name=message.guild.name),
    #     query=mongo_query,
    #     data={
    #         "$set": {
    #             "summary": thread_summary
    #         }
    #     }
    # )