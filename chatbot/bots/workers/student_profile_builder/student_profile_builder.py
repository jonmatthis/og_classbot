import logging
from typing import Type

import tiktoken
from dotenv import load_dotenv
from langchain import PromptTemplate, OpenAI
from langchain.callbacks import get_openai_callback
from langchain.chains import LLMChain
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatAnthropic
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from pydantic import BaseModel
from pymongo.collection import Collection
from rich import print

from chatbot.bots.workers.student_profile_builder.student_profile_builder_prompt import old_STUDENT_SUMMARY_UPDATE_PROMPT_TEMPLATE
from chatbot.bots.workers.thread_summarizer.thread_summarizer_prompts import REFINE_THREAD_SUMMARY_PROMPT_TEMPLATE
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

MAX_TOKEN_COUNT = 2048

load_dotenv()

logger = logging.getLogger(__name__)


class StudentProfileBuilder:
    def __init__(self,
                 mongo_database: MongoDatabaseManager,
                 thread_collection_name: str,
                 student_profile_collection_name: str,
                 overwrite_existing: bool = False,
                 use_anthropic: bool = False,

                 ):
        self.overwrite_existing = overwrite_existing
        self._mongo_database = mongo_database
        self._thread_collection = self._mongo_database.get_collection(thread_collection_name)
        self._student_profile_collection_name = student_profile_collection_name
        self._student_profile_collection = self._mongo_database.get_collection(student_profile_collection_name)

        self.base_summary_prompt = PromptTemplate(
            template=old_STUDENT_SUMMARY_UPDATE_PROMPT_TEMPLATE,
            input_variables=["text"])

        self.refine_prompt = PromptTemplate(
            template=REFINE_THREAD_SUMMARY_PROMPT_TEMPLATE,
            input_variables=["existing_answer", "text"])

        if use_anthropic:
            if os.getenv("ANTHROPIC_API_KEY") is None:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.llm = ChatAnthropic(temperature=0, max_tokens_to_sample=1000)
            self.llm_model = self.llm.model
            self.dollars_per_token = 0.00000163
        if not use_anthropic or self.llm is None:
            self.llm = OpenAI(temperature=0, max_tokens=1000)
            self.llm_model = self.llm.model_name
            self.dollars_per_token = 0.00002

        self.chain = load_summarize_chain(self.llm,
                                          chain_type="map_reduce",
                                          verbose=True,
                                          question_prompt=self.base_summary_prompt,
                                          refine_prompt=self.refine_prompt
                                          )
    def _configure_llm(self, ):
        self._chain = load_summarize_chain(llm = self._smart_llm,
                                           chain_type="map_reduce",
                                           return_intermediate_step=True)

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
            template=old_STUDENT_SUMMARY_UPDATE_PROMPT_TEMPLATE,
            input_variables=['current_student_summary',
                             'conversation_summary',
                             # 'conversation'
                             ], )

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
                               # conversation: str
                               ) -> str:

        return self._summary_update_chain.predict(
            current_student_summary=current_student_summary,
            conversation_summary=conversation_summary,
            # conversation=conversation
        )

    def retrieve_current_student_summary(self, collection: Collection, query):
        document = collection.find_one(query)
        if document is not None:
            try:
                student_summary = document['student_summary']
                return student_summary
            except Exception as e:
                return ""


    def retrieve_current_model(self, collection: Collection, query, pydantic_model: Type[BaseModel]) -> BaseModel:
        document = collection.find_one(query)
        if document is None:
            return pydantic_model()

        try:
            student_profile = document['student_profile']
            return pydantic_model(**student_profile) if student_profile else pydantic_model()
        except KeyError:
            return pydantic_model()

    def generate_student_profiles(self):
        number_of_students = len(self._student_usernames)
        with get_openai_callback() as cb:
            for student_number, student_username in enumerate(self._student_usernames):
                print(f"-----------------------------------------------------------------------------\n"
                      f"-----------------------------------------------------------------------------\n"
                      f"Generating profile for {student_username}  - {student_number + 1} of {number_of_students}\n"
                      f"-----------------------------------------------------------------------------\n")

                mongo_query = {"discord_username": student_username}
                student_threads = [thread for thread in
                                   self._thread_collection.find({'thread_owner_name': student_username})]

                # current_student_model = self.retrieve_current_model(collection=self._student_profile_collection,
                #                                                     query=mongo_query,
                #                                                     pydantic_model=StudentProfileSchema)
                # print(f"Current model (before update):\n{current_student_model}\n")

                current_student_summary = self.retrieve_current_student_summary(
                    collection=self._student_profile_collection,
                    query=mongo_query)
                print(f"Current summary (before update):\n{current_student_summary}\n")

                if  current_student_summary is not None and not self.overwrite_existing:
                    print(f"Student Summary already exists - skipping!\n")
                    continue

                self._mongo_database.upsert(collection=self._student_profile_collection_name,
                                            query=mongo_query,
                                            data={"$set": {"threads": student_threads}})
                for thread_number, thread in enumerate(student_threads):
                    print(f"--------------Thread#{thread_number}-of-{len(student_threads)}-------------\n")
                    print(f"Updating model based on thread with summary:\n {thread['summary']}\n")

                    current_student_summary = self.update_student_summary(
                        current_student_summary=current_student_summary,
                        conversation_summary=thread['summary'],)
                        # conversation=thread_as_str)

                    print(f"Current summary (after update):\n{current_student_summary}\n\n---\n\n")
                    print(f"OpenAI API callback:\n {cb}\n")

                    self._mongo_database.upsert(collection=self._student_profile_collection_name,
                                                query=mongo_query,
                                                data={"$set": {"student_summary": current_student_summary}})

        self._mongo_database.save_json(collection_name=self._student_profile_collection_name,)


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


if __name__ == '__main__':
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"
    thread_collection_name = get_thread_backups_collection_name(server_name=server_name)
    student_profile_collection_name = "student_profiles"
    student_profile_builder = StudentProfileBuilder(mongo_database=MongoDatabaseManager(),
                                      thread_collection_name=thread_collection_name,
                                      student_profile_collection_name=student_profile_collection_name,
                                    overwrite_existing=True
                                      )
    student_profile_builder.generate_student_profiles()
