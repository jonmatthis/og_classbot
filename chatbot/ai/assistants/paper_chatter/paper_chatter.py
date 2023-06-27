import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.vectorstores import Chroma

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager

load_dotenv()
from langchain import LLMChain, OpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory, VectorStoreRetrieverMemory, CombinedMemory
from langchain.prompts import (
    HumanMessagePromptTemplate,
    ChatPromptTemplate, SystemMessagePromptTemplate,
)

PAPER_CHATTER_SYSTEM_TEMPLATE = """
            You are a teaching assistant for the course: Neural Control of Real-World Human Movement. 
               
            Course Description:
            In this interdisciplinary course, students will explore the neural basis of natural human behavior in real-world contexts (e.g., sports, dance, or everyday activities) by investigating the neural control of full-body human movement. The course will cover philosophical, technological, and scientific aspects related to the study of natural behavior while emphasizing hands-on, project-based learning. Students will use free open-source machine-learning and computer-vision-driven tools and methods to record human movement in unconstrained environments.
            The course promotes interdisciplinary collaboration and introduces modern techniques for decentralized project management, AI-assisted research techniques, and Python-based programming (No prior programming experience is required). Students will receive training in the use of AI technology for project management and research conduct, including literature review, data analysis, and presentation of results. Through experiential learning, students will develop valuable skills in planning and executing technology-driven research projects while examining the impact of structural inequities on scientific inquiry.
            The primary focus is on collaborative work where each student will contribute to a shared research project on their interests/skillsets (e.g. some students will do more programming, others will do more lit reviewing, etc).

            Course Objectives:
            - Gain exposure to key concepts related to neural control of human movement.
            - Apply interdisciplinary approaches when collaborating on complex problems.
            - Develop a basic understanding of machine-learning tools for recording human movements.
            - Contribute effectively within a team setting towards achieving common goals.
            - Acquire valuable skills in data analysis or background research.

            ----

            Your personality is friendly, empathetic, curious, detail-oriented, attentive, and resourceful. Excited to learn and teach and explore and grow!

            Your conversational style is:
            - You give short answers (1-2 sentences max) to answer questions.
            - You speak in a casual and friendly manner.
            - Use your own words and be yourself!
            
            ----
             Here is the current conversation history: 

             ``` 
             {chat_memory} 
             ```


            
            Here are some relevant papers that  you know about:
            ```
            {vectorstore_memory}
            ```
            """

class PaperChatter:
    def __init__(self,
                 chat_llm,
                 prompt,
                 memory,):
        self._chat_llm = chat_llm
        self._prompt = prompt
        self._memory = memory
        self._chain = self._create_llm_chain()

    @classmethod
    async def create(cls,
                     temperature=0.8,
                     model_name="gpt-4",
                     prompt_template=PAPER_CHATTER_SYSTEM_TEMPLATE):
        chat_llm = ChatOpenAI(
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=temperature,
            model_name=model_name,
        )

        prompt = cls._create_prompt(prompt_template=prompt_template)
        memory = await cls._configure_memory(cls)

        return cls(chat_llm, prompt, memory)



    async def _configure_memory(self):
        conversation_memory = self._configure_conversation_memory(self)
        vectorstore_memory = await self._configure_vectorstore_memory(self)
        combined_memory = CombinedMemory(memories=[conversation_memory,
                                                   vectorstore_memory])
        return combined_memory

    async def _configure_vectorstore_memory(self):
        collection_name = "green_check_messages"

        mongo_database = MongoDatabaseManager()

        collection = mongo_database.get_collection(collection_name)
        all_entries = await collection.find().to_list(length=None)


        print("Creating vector store from {collection_name} collection with {len(all_entries)} entries")

        documents = []
        for entry in all_entries:
            documents.append(Document(page_content=entry["parsed_output_string"],
                                      metadata={"_student_uuid": entry["_student_uuid"],
                                                "thread_url": entry["thread_url"],
                                                "source": entry["parsed_output_dict"]["citation"],
                                                **entry["parsed_output_dict"], }))

        embeddings = OpenAIEmbeddings()
        chroma_vector_store = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                collection_name=collection_name,
                persist_directory=str(Path(os.getenv("PATH_TO_CHROMA_PERSISTENCE_FOLDER")) / collection_name),
            )

        retriever = chroma_vector_store.as_retriever(search_kwargs=dict(k=3))

        return VectorStoreRetrieverMemory(retriever=retriever,
                                          memory_key="vectorstore_memory",
                                          input_key="human_input",)



    def _configure_conversation_memory(self):
        return ConversationSummaryBufferMemory(memory_key="chat_memory",
                                               input_key="human_input",
                                               llm=OpenAI(temperature=0),
                                               max_token_limit=1000)

    def _create_llm_chain(self):
        return LLMChain(llm=self._chat_llm,
                        prompt=self._prompt,
                        memory=self._memory,
                        verbose=True,
                        )

    def _create_prompt(prompt_template: str):
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            prompt_template
        )

        human_template = "{human_input}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            human_template
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [system_message_prompt, human_message_prompt]
        )

        return chat_prompt

    async def async_process_input(self, input_text):
        print(f"Input: {input_text}")
        print("Streaming response...\n")
        ai_response = await self._chain.arun(human_input=input_text)
        return ai_response

    async def demo(self):
        print("Welcome to the Neural Control Assistant demo!")
        print("Type 'exit' to end the demo.\n")

        while True:
            input_text = input("Enter your input: ")

            if input_text.strip().lower() == "exit":
                print("Ending the demo. Goodbye!")
                break

            response = await self.async_process_input(input_text)

            print("\n")

    async def load_memory_from_thread(self, thread, bot_name: str):
        async for message in thread.history(limit=None, oldest_first=True):
            if message.content == "":
                continue
            if str(message.author) == bot_name:
                self._memory.chat_memory.add_ai_message(message.content)
            else:
                self._memory.chat_memory.add_user_message(message.content)


if __name__ == "__main__":
    async def main():
        paper_chatter = await PaperChatter.create()
        await paper_chatter.demo()


    asyncio.run(main())