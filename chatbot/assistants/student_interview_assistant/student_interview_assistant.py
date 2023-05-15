import logging
from typing import List, Type

from langchain import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection

from chatbot.assistants.student_interview_assistant.prompt_templates.model_updater_prompt_template import MODEL_UPDATE_PROMPT_TEMPLATE
from chatbot.assistants.student_interview_assistant.models import UpsertPayload, ModelUpdateResponse, ModelUpdatePayload, \
    StudentInterviewSchema, InterviewGuidance
from chatbot.assistants.student_interview_assistant.prompt_templates.interview_guidance_prompt_template import INTERVIEW_GUIDANCE_PROMPT_TEMPLATE

logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
load_dotenv()

class ConversationAssistant:
    def __init__(self):
        self._smart_llm = ChatOpenAI(model_name='gpt-4')
        self._not_as_smart_llm = ChatOpenAI(model_name='gpt-3.5-turbo')

    def update_model(self, input_payload: ModelUpdatePayload) -> BaseModel:

        print(input_payload)
        pydantic_class_constructor = input_payload.model.__class__

        extractor_parser = PydanticOutputParser(pydantic_object=pydantic_class_constructor)

        model_update_prompt = PromptTemplate(
            template=MODEL_UPDATE_PROMPT_TEMPLATE,
            input_variables=['current_model',
                             'ai_question',
                             'human_response'],
            partial_variables={'format_instructions': extractor_parser.get_format_instructions()}
        )

        extractor_chain = LLMChain(
            prompt=model_update_prompt,
            llm=self._not_as_smart_llm
        )

        fixer = OutputFixingParser.from_llm(
            llm=self._not_as_smart_llm,
            parser=extractor_parser
        )

        raw_response = extractor_chain.predict(
            ai_question=input_payload.ai_question,
            human_response=input_payload.human_answer,
            current_model=input_payload.model
        )

        updated_model = fixer.parse(
            raw_response
        )

        return updated_model

    def get_questions(self, current_model: BaseModel) -> List[str]:
        interview_guidance_parser = PydanticOutputParser(pydantic_object=InterviewGuidance)

        interview_guidance_prompt = PromptTemplate(
            template=INTERVIEW_GUIDANCE_PROMPT_TEMPLATE,
            input_variables=['current_model'],
            partial_variables={'format_instructions': interview_guidance_parser.get_format_instructions()}
        )

        interview_guidance_chain = LLMChain(
            prompt=interview_guidance_prompt,
            llm=self._smart_llm
        )

        output_fixing_parser = OutputFixingParser.from_llm(
            llm=self._not_as_smart_llm,
            parser=interview_guidance_parser
        )

        raw_response = interview_guidance_chain.predict(
            current_model=current_model
        )

        question_list = output_fixing_parser.parse(
            raw_response
        )

        return question_list.questions

    def retrieve(self, collection: Collection, query, pydantic_model: Type[BaseModel]) -> BaseModel:
        document = collection.find_one(query)
        return pydantic_model(**document) if document else pydantic_model()
    def mongo_update(self, collection: Collection, query: dict, model: BaseModel):
        collection.update_one(query, {"$set": model.dict()}, upsert=True)

    def handle_model_update(self, input: UpsertPayload) -> ModelUpdateResponse:

        updated_model = self.update_model(ModelUpdatePayload(
            ai_question=input.ai_question,
            human_answer=input.human_answer,
            model=input.model
        ))

        new_questions = self.get_questions(updated_model)

        self.mongo_update(input.collection, input.query, updated_model)

        output_payload = ModelUpdateResponse(
            questions=new_questions,
            model=updated_model
        )

        return output_payload


if __name__ == '__main__':
    assistant = ConversationAssistant()

    # Create a client instance
    client = MongoClient("mongodb://localhost:27017/")

    # Select a database
    db = client["test"]

    # Select a collection
    collection = db["test"]

    query = {
        'id': '12345'
    }

    model = assistant.retrieve(collection, query, StudentInterviewSchema)

    payload = UpsertPayload(
        ai_question="Tell me a little about yourself",
        human_answer="Hello! My name is Jon and I'm the prof of this here server. I love to study and teach about the neural control of human movement in the real world. I'm especially interested in eye tracking, musculoskeletal biomechanics, and robotics 🧠  🤖 ✨ In this course, I hope to learn about how to manage a course based that teaches students how to conduct technical, collaborative research projects using the decentralized project management methods from the free-open-source software (FOSS) community",
        collection=collection,
        model=model,
        query=query
    )

    payloads = {}
    payloads[0] = payload

    loop = 5
    for loop_index in range(loop):
        print(f'------loop index: {loop_index}------\n')

        model_update_response = assistant.handle_model_update(payloads[loop_index])

        print(f'\n--Updated model: {model_update_response.model.dict()}--\n')

        print(f'new questions: {model_update_response.questions}-\n')

        print(f"Asking question: {model_update_response.questions[0]}-\n")

        human_answer = input("Human answer: ")

        payloads[loop_index + 1] = UpsertPayload(
            ai_question=model_update_response.questions[0],
            human_answer=human_answer,
            collection=collection,
            model=model_update_response.model,
            query=query
        )

    best_guess_model = model_update_response.model

    print(f"=========\n+++++++++++\n==========\nBest guess model:\n {best_guess_model}\n==========\n+++++++++++\n==========\n")
