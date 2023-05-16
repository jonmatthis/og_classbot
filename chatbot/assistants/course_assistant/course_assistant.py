import asyncio
from datetime import datetime

from dotenv import load_dotenv

from chatbot.assistants.course_assistant.course_assistant_prompt import COURSE_ASSISTANT_SYSTEM_TEMPLATE

load_dotenv()
from langchain import LLMChain, OpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from pymongo.collection import Collection

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager, TEST_MONGO_QUERY


class CourseAssistant:
    def __init__(self,
                 mongo_collection: Collection,
                 temperature=0.8,
                 model_name="gpt-4",
                 mongo_query: dict = TEST_MONGO_QUERY,
                 ):

        self._mongo_collection = mongo_collection
        self._chat_llm = ChatOpenAI(
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=temperature,
            model_name=model_name,
        )

        self._mongo_query = mongo_query

        self._chat_prompt = self._create_chat_prompt()
        self._chat_memory = self._configure_chat_memory()

        self._chain = self._create_llm_chain()

    @property
    def conversation_summary(self):
        return self._chat_memory.moving_summary_buffer

    def _configure_chat_memory(self):
        # return ConversationBufferMemory(memory_key="chat_history")
        return ConversationSummaryBufferMemory(memory_key="chat_history",
                                               llm=OpenAI(),
                                               max_token_limit=50)

    def _create_llm_chain(self):
        self._update_chat_history(role="system",
                                  input_text=COURSE_ASSISTANT_SYSTEM_TEMPLATE)
        return LLMChain(llm=self._chat_llm,
                        prompt=self._chat_prompt,
                        memory=self._chat_memory,
                        verbose=True,
                        )

    def _create_chat_prompt(self):
        self._system_message_prompt = SystemMessagePromptTemplate.from_template(
            COURSE_ASSISTANT_SYSTEM_TEMPLATE
        )
        human_template = "{human_input}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            human_template
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [self._system_message_prompt, human_message_prompt]
        )

        return chat_prompt

    def _update_chat_memory(self):
        try:
            update_operation = {
                "$set": {
                    "chat_memory.conversation_summary": self.conversation_summary,
                    "chat_memory.message_buffer": [
                        message.dict() for message in self._chat_memory.chat_memory.messages
                    ],
                },
            }
            self._mongo_collection.update_one(self._mongo_query, update_operation, upsert=True)

        except Exception as e:
            print(f"Error updating chat memory: {e}")

    def _update_chat_history(self, role: str,
                             input_text: str):
        try:
            self._mongo_collection.update_one(self._mongo_query,
                                              {"$push": {"messages": {"role": role,
                                                                      "content": input_text,
                                                                      "timestamp": datetime.now().isoformat(),
                                                                      }
                                                         }
                                               },
                                              upsert=True)
        except Exception as e:
            print(f"Error updating chat history: {e}")

    async def async_process_input(self, input_text):
        print(f"Input: {input_text}")
        print("Streaming response...\n")
        self._update_chat_history(role="user",
                                  input_text=input_text)

        ai_response = await self._chain.arun(human_input=input_text)
        self._update_chat_history(role="assistant",
                                  input_text=ai_response)
        self._update_chat_memory()
        return ai_response

    async def demo(self):
        print("Welcome to the Neural Control Assistant demo!")
        print("You can ask questions or provide input related to the course.")
        print("Type 'exit' to end the demo.\n")

        while True:
            input_text = input("Enter your input: ")

            if input_text.strip().lower() == "exit":
                print("Ending the demo. Goodbye!")
                break

            response = await self.async_process_input(input_text)

            print("\n")


if __name__ == "__main__":
    assistant = CourseAssistant(mongo_collection=MongoDatabaseManager().get_collection("test_collection"))
    asyncio.run(assistant.demo())
