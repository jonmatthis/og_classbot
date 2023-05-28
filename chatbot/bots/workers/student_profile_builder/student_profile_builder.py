import logging
from typing import Type

import tiktoken
from dotenv import load_dotenv
from langchain import PromptTemplate
from langchain.callbacks import get_openai_callback
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from pydantic import BaseModel
from pymongo.collection import Collection
from rich import print

from chatbot.bots.workers.student_profile_builder.models import StudentProfileSchema
from chatbot.bots.workers.student_profile_builder.student_profile_builder_prompt import \
    STUDENT_PROFILE_UPDATE_PROMPT_TEMPLATE, STUDENT_SUMMARY_UPDATE_PROMPT_TEMPLATE
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

MAX_TOKEN_COUNT = 2048

load_dotenv()

logger = logging.getLogger(__name__)


class StudentProfileBuilder:
    def __init__(self,
                 mongo_database: MongoDatabaseManager,
                 thread_collection_name: str,
                 student_profile_collection_name: str,

                 ):

        self._mongo_database = mongo_database
        self._thread_collection = self._mongo_database.get_collection(thread_collection_name)
        self._student_profile_collection_name = student_profile_collection_name
        self._student_profile_collection = self._mongo_database.get_collection(student_profile_collection_name)

        self._student_usernames = self._thread_collection.distinct("thread_owner_name")

        self._smart_llm = ChatOpenAI(model_name='gpt-4')
        self._not_as_smart_llm = ChatOpenAI(model_name='gpt-3.5-turbo')

        self._configure_llms(student_profile_schema=StudentProfileSchema)

    def _configure_llms(self, student_profile_schema: Type[BaseModel]):

        self._student_profile_extractor_parser = PydanticOutputParser(pydantic_object=student_profile_schema)
        student_profile_update_prompt = PromptTemplate(
            template=STUDENT_PROFILE_UPDATE_PROMPT_TEMPLATE,
            input_variables=['current_model',
                             'summary',
                             'conversation',
                             ],
            partial_variables={'format_instructions': self._student_profile_extractor_parser.get_format_instructions()}
        )
        self._model_update_chain = LLMChain(
            prompt=student_profile_update_prompt,
            llm=self._smart_llm,
            verbose=True
        )
        self._output_fixing_parser = OutputFixingParser.from_llm(
            llm=self._not_as_smart_llm,
            parser=self._student_profile_extractor_parser,
        )

        self._summary_update_prompt = PromptTemplate(
            template=STUDENT_SUMMARY_UPDATE_PROMPT_TEMPLATE,
            input_variables=['current_student_summary', 'conversation_summary', 'conversation'], )

        self._summary_update_chain = LLMChain(
            prompt=self._summary_update_prompt,
            llm=self._smart_llm,
            verbose=True
        )

    def update_student_model(self,
                             summary: str,
                             conversation: str,
                             current_model: BaseModel) -> BaseModel:

        raw_response = self._model_update_chain.predict(
            summary=summary,
            conversation=conversation,
            current_model=current_model
        )

        updated_student_model = self._output_fixing_parser.parse(
            raw_response
        )
        return updated_student_model

    def update_student_summary(self,
                               current_student_summary: str,
                               conversation_summary: str,
                               conversation: str) -> str:

        return self._summary_update_chain.predict(
            current_student_summary=current_student_summary,
            conversation_summary=conversation_summary,
            conversation=conversation
        )

    def retrieve_current_student_summary(self, collection: Collection, query) -> str:
        document = collection.find_one(query)
        if document is not None:
            student_summary = document['student_summary']
            return student_summary if student_summary else ""

        return ""

    def retrieve_current_model(self, collection: Collection, query, pydantic_model: Type[BaseModel]) -> BaseModel:
        document = collection.find_one(query)
        document = collection.find_one(query)
        if document is None:
            return pydantic_model()
        student_profile = document['student_profile']
        return pydantic_model(**student_profile) if student_profile else pydantic_model()

    def update_mongo(self, collection: Collection, query: dict, data: dict):
        self._mongo_database.upsert(collection=collection,
                                    query=query,
                                    data=data)

    def generate_student_profiles(self):

        with get_openai_callback() as cb:
            for student_username in self._student_usernames:
                print(f"-----------------------------------------------------------------------------\n"
                      f"-----------------------------------------------------------------------------\n"
                      f"Generating profile for {student_username}")
                mongo_query = {"discord_username": student_username}
                student_threads = [thread for thread in
                                   self._thread_collection.find({'thread_owner_name': student_username})]

                current_student_model = self.retrieve_current_model(collection=self._student_profile_collection,
                                                                    query=mongo_query,
                                                                    pydantic_model=StudentProfileSchema)
                print(f"Current model (before update):\n{current_student_model}\n")

                current_student_summary = self.retrieve_current_student_summary(
                    collection=self._student_profile_collection,
                    query=mongo_query)
                print(f"Current summary (before update):\n{current_student_summary}\n")

                self._mongo_database.upsert(collection=self._student_profile_collection_name,
                                            query=mongo_query,
                                            data={"$set": {"threads": student_threads}})
                for thread in student_threads:
                    print(f"Updating model based on thread with summary:\n {thread['summary']}\n")
                    thread_as_str = "\n".join(thread['thread_as_list_of_strings'])
                    full_thread_token_count = num_tokens_from_string(thread_as_str, model=self._smart_llm.model_name)
                    if full_thread_token_count > MAX_TOKEN_COUNT:
                        print(
                            f"Thread is too long ({full_thread_token_count} tokens), not sending full conversation to model")
                        thread_as_str = ""

                        current_student_model = self.update_student_model(summary=thread['summary'],
                                                                          conversation=thread_as_str,
                                                                          current_model=current_student_model)
                        print(f"Current model (after update):\n{current_student_model}\n\n---\n\n")


                        current_student_summary = self.update_student_summary(
                            current_student_summary=current_student_summary,
                            conversation_summary=thread['summary'],
                            conversation=thread_as_str)

                        print(f"Current summary (after update):\n{current_student_summary}\n\n---\n\n")
                        print(f"OpenAI API callback:\n {cb}\n")

                    self._mongo_database.upsert(collection=self._student_profile_collection_name,
                                                query=mongo_query,
                                                data={"$set": {"student_summary": current_student_summary}})


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


if __name__ == '__main__':
    thread_collection_name = "thread_backups_for_Neural Control of Real World Human Movement 2023 Summer1"
    student_profile_collection_name = "student_profiles"
    assistant = StudentProfileBuilder(mongo_database=MongoDatabaseManager(),
                                      thread_collection_name=thread_collection_name,
                                      student_profile_collection_name=student_profile_collection_name,

                                      )
    assistant.generate_student_profiles()
