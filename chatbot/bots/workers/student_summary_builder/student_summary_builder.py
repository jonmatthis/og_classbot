import asyncio
import logging
from datetime import datetime

import tiktoken
from dotenv import load_dotenv
from langchain import PromptTemplate, LLMChain
from langchain.callbacks import get_openai_callback
from langchain.chat_models import ChatOpenAI

from chatbot.bots.workers.student_summary_builder.student_summary_builder_prompts import \
    STUDENT_SUMMARY_BUILDER_PROMPT_TEMPLATE
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name, STUDENT_SUMMARIES_COLLECTION_NAME

MAX_TOKEN_COUNT = 2048

load_dotenv()

logger = logging.getLogger(__name__)


class StudentSummaryBuilder:
    def __init__(self,
                 mongo_database: MongoDatabaseManager,
                 thread_collection_name: str,
                 student_summaries_collection_name: str,
                 use_anthropic: bool = False,
                 ):
        self._mongo_database = mongo_database
        self._thread_collection = self._mongo_database.get_collection(thread_collection_name)
        self._student_summaries_collection_name = student_summaries_collection_name
        self._student_summaries_collection = self._mongo_database.get_collection(student_summaries_collection_name)

        self._student_usernames = self._thread_collection.distinct("thread_owner_name")

        self.student_summary_builder_prompt = PromptTemplate(
            template=STUDENT_SUMMARY_BUILDER_PROMPT_TEMPLATE,
            input_variables=["current_student_summary", "new_conversation_summary"])

        self.llm = ChatOpenAI(model_name='gpt-4', temperature=0, max_tokens=1000)
        self.llm_model = self.llm.model_name
        self.dollars_per_token = 0.00003  # gpt-4

        self._summary_update_chain = LLMChain(llm=self.llm,
                                              prompt=self.student_summary_builder_prompt,
                                              verbose=True,
                                              )

    async def update_student_summary_based_on_new_conversation(self,
                                                               current_student_summary: str,
                                                               new_conversation_summary: str,
                                                               ) -> str:

        return await self._summary_update_chain.apredict(
            current_student_summary=current_student_summary,
            new_conversation_summary=new_conversation_summary,
        )

    async def generate_student_summaries(self):
        number_of_students = len(self._student_usernames)
        with get_openai_callback() as cb:
            for student_number, student_username in enumerate(self._student_usernames):
                print(f"-----------------------------------------------------------------------------\n"
                      f"Generating profile for {student_username}"
                      f"Student#{student_number + 1} of {number_of_students}\n"
                      f"-----------------------------------------------------------------------------\n")

                student_threads = [thread for thread in
                                   self._thread_collection.find({'thread_owner_name': student_username})]

                self._mongo_database.upsert(collection=self._student_summaries_collection_name,
                                            query={"discord_username": student_username},
                                            data={"$set": {"threads": student_threads}})

                for thread_number, thread in enumerate(student_threads):
                    thread_summary = thread['summary']['summary']
                    print(f"---------Incorporating Thread#{thread_number + 1}-of-{len(student_threads)}-------------\n")
                    print(f"Updating student summary based on thread with summary:\n {thread_summary}\n")

                    student_summary_entry = self._student_summaries_collection.find_one(
                        {"discord_username": student_username})
                    try:
                        current_student_summary = student_summary_entry.get("student_summary", "")
                    except Exception as e:
                        current_student_summary = ""

                    print(f"Current student summary (before update):\n{current_student_summary}\n")

                    updated_student_summary = await self.update_student_summary_based_on_new_conversation(
                        current_student_summary=current_student_summary,
                        new_conversation_summary=thread_summary, )

                    print(f"Updated summary (after update):\n{updated_student_summary}\n\n---\n\n")
                    print(f"OpenAI API callback:\n {cb}\n")

                    self._mongo_database.upsert(collection=self._student_summaries_collection_name,
                                                query={"discord_username": student_username},
                                                data={"$set": {"student_summary": {"summary": updated_student_summary,
                                                                                   "created_at": datetime.now().isoformat(),
                                                                                   "model": self.llm_model}}},
                                                )
                    if student_summary_entry is not None:
                        if "student_summary" in student_summary_entry:
                            self._mongo_database.upsert(collection=self._student_summaries_collection_name,
                                                        query={"discord_username": student_username},
                                                        data={"$push": {"previous_summaries": student_summary_entry["student_summary"]}}
                                                        )

        self._mongo_database.save_json(collection_name=self._student_summaries_collection_name, )


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)
    student_profile_builder = StudentSummaryBuilder(mongo_database=MongoDatabaseManager(),
                                                    thread_collection_name=thread_collection_name,
                                                    student_summaries_collection_name=STUDENT_SUMMARIES_COLLECTION_NAME,
                                                    )
    asyncio.run(student_profile_builder.generate_student_summaries())
