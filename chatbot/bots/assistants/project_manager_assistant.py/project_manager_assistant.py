import logging
from typing import List, Type

from dotenv import load_dotenv
from langchain import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from pydantic import BaseModel
from pymongo.collection import Collection

from chatbot.bots.workers.student_profile_builder.models import UpsertPayload, ModelUpdateResponse, \
    ModelUpdatePayload, \
    StudentInterviewSchema, InterviewGuidance
from chatbot.bots.workers.student_profile_builder.student_profile_builder_prompt import \
    INTERVIEW_GUIDANCE_PROMPT_TEMPLATE, MODEL_UPDATE_PROMPT_TEMPLATE
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

load_dotenv()

logger = logging.getLogger(__name__)


class StudentInterviewAssistant:
    def __init__(self,
                 student_user_id: int,
                 collection: Collection,
                 initial_human_message: str = "Hello, let's get started!"):
        self._student_user_id = student_user_id

        self._collection = collection

        self._previous_ai_question = 'Hello! Tell me a little about yourself.'
        self._initial_human_message = initial_human_message

        self._student_id_query = {'id': test_student_user_id}

        self._current_student_model = self.retrieve_current_model(collection=self._collection,
                                                                  query=self._student_id_query,
                                                                  pydantic_model=StudentInterviewSchema)

        self._smart_llm = ChatOpenAI(model_name='gpt-4')
        self._not_as_smart_llm = ChatOpenAI(model_name='gpt-3.5-turbo')

        self._configure_llms()

    def _configure_llms(self):
        pydantic_class_constructor = StudentInterviewSchema
        self._extractor_parser = PydanticOutputParser(pydantic_object=pydantic_class_constructor)
        model_update_prompt = PromptTemplate(
            template=MODEL_UPDATE_PROMPT_TEMPLATE,
            input_variables=['current_model',
                             'ai_question',
                             'human_response'],
            partial_variables={'format_instructions': self._extractor_parser.get_format_instructions()}
        )
        self._extractor_chain = LLMChain(
            prompt=model_update_prompt,
            llm=self._smart_llm
        )
        self._output_fixing_parser = OutputFixingParser.from_llm(
            llm=self._not_as_smart_llm,
            parser=self._extractor_parser
        )
        self._interview_guidance_parser = PydanticOutputParser(pydantic_object=InterviewGuidance)

        interview_guidance_prompt = PromptTemplate(
            template=INTERVIEW_GUIDANCE_PROMPT_TEMPLATE,
            input_variables=['current_model'],
            partial_variables={'format_instructions': self._interview_guidance_parser.get_format_instructions()}
        )

        self._interview_guidance_chain = LLMChain(
            prompt=interview_guidance_prompt,
            llm=self._smart_llm
        )

        self._output_fixing_parser = OutputFixingParser.from_llm(
            llm=self._not_as_smart_llm,
            parser=self._interview_guidance_parser
        )

    def update_student_model(self, model_update_payload: ModelUpdatePayload) -> BaseModel:
        logger.info(f"Updating student model for {self._student_user_id} with {model_update_payload}")

        raw_response = self._extractor_chain.predict(
            ai_question=model_update_payload.ai_question,
            human_response=model_update_payload.human_answer,
            current_model=model_update_payload.model
        )

        updated_student_model = self._output_fixing_parser.parse(
            raw_response
        )

        return updated_student_model

    def get_interview_questions(self, current_model: BaseModel) -> List[str]:
        logger.info(f"Getting interview questions for {self._student_user_id} with {current_model}")
        raw_response = self._interview_guidance_chain.predict(
            current_model=current_model
        )

        question_list = self._output_fixing_parser.parse(
            raw_response
        )

        return question_list.questions

    def retrieve_current_model(self, collection: Collection, query, pydantic_model: Type[BaseModel]) -> BaseModel:
        document = collection.find_one(query)
        return pydantic_model(**document) if document else pydantic_model()

    def update_mongo(self, collection: Collection, query: dict, model: BaseModel):
        collection.update_one(query, {"$set": model.dict()}, upsert=True)

    def handle_model_update(self, upsert_payload: UpsertPayload) -> ModelUpdateResponse:
        logger.info(f"Handling model update for {self._student_user_id} with {upsert_payload}")
        updated_model = self.update_student_model(ModelUpdatePayload(
            ai_question=upsert_payload.ai_question,
            human_answer=upsert_payload.human_answer,
            model=upsert_payload.model
        ))

        self.update_mongo(upsert_payload.collection, upsert_payload.query, updated_model)

        new_questions = self.get_interview_questions(updated_model)

        output_payload = ModelUpdateResponse(
            questions=new_questions,
            model=updated_model
        )

        return output_payload

    def _get_response(self, human_input: str):
        logger.info(f"Getting response for {self._student_user_id} with input {human_input}")
        upsert_payload = UpsertPayload(
            ai_question=self._previous_ai_question,
            human_answer=human_input,
            collection=self._collection,
            model=self._current_student_model,
            query=self._student_id_query
        )
        model_update_response = self.handle_model_update(upsert_payload)
        self._previous_ai_question = model_update_response.questions[0]
        return self._previous_ai_question

    def process_input(self, input_text):
        print(f"Awaiting response (it's slow, be patient)...")
        response = self._get_response(human_input=input_text)
        return response

    def demo(self, number_of_loops: int = 3):
        from rich import print
        print("Welcome to the Neural Control Assistant demo!")
        print("You can ask questions or provide input related to the course.")
        print("Type 'exit' to end the demo.\n")

        for loop in range(number_of_loops):
            print(f"=======\nLoop {loop + 1}:\n========\n")
            print(f"\nCurrent Model:\n {self._current_student_model.dict()}\n--------\n")

            print(self.process_input(input_text=self._initial_human_message))

            input_text = input("Enter your input: ")

            if input_text.strip().lower() == "exit":
                print("Ending the demo. Goodbye!")
                break

            response = self.process_input(input_text)

            print(f"Response: {response}")

            print("\n")


if __name__ == '__main__':
    test_student_user_id = 1111
    collection_name_in = "test_student_interview_assistant"
    assistant = StudentInterviewAssistant(student_user_id=test_student_user_id,
                                          collection=MongoDatabaseManager().get_collection(collection_name_in),
                                          )
    assistant.demo()
