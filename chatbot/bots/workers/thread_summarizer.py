import logging
import os
from typing import List, Tuple

from langchain import OpenAI, PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatAnthropic
from langchain.schema import Document

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

logger = logging.getLogger(__name__)

THREAD_SUMMARY_PROMPT_TEMPLATE = """
You are a course assistant for the follow course (course information is between four plus signs ++++ like ++++)
++++
Title: 
Neural Control of Real-World Human Movement

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
++++

Your current task is to: 

Examine conversations between the student and a chatbot in order to determine the students interests and skillset. 
This information will be used to help guide the student through this course and ensure they get as much out of it as they can 

NOTE -sometimes a human will try to poke at the boundaries of what the bot is allowed or capable of doing.
When this happens, recognize it as meaning that the human has an interest in Machine Learning, AI, and cybersecurity

Here is the latest conversation:

{text}

----------------
In your answer do NOT include ANY:
 - pre-amble (such as "Here is the summary" or "The refined summary is"),
 - post-script (such as "Does this summary and recommendations seem accurate?" or  "Let me know if you have any other questions!")
...or any other text that is not part of the summary itself.
"""

REFINE_PROMPT_TEMPLATE = """
    Your job is to produce a final summary 
    We have provided an existing summary up to a certain point: {existing_answer}
    We have the opportunity to refine the existing summary
    (only if needed) with some more context below.
    ------------
    {text}
    ------------
    Given the new context, refine the original summary
    If the context isn't useful, return the original summary.
    
    In your answer do NOT include ANY:
     - pre-amble (such as "Here is the summary" or "The refined summary is"),
     - post-script (such as "Does this summary and recommendations seem accurate?" or  "Let me know if you have any other questions!")
    ...or any other text that is not part of the summary itself.
"""


class ThreadSummarizer:
    def __init__(self,
                 thread_data: List[str],
                 use_anthropic: bool = False,
                 max_tokens_per_chunk: int = 1000):
        self.thread_data = thread_data
        self.max_tokens_per_chunk = max_tokens_per_chunk

        self.base_summary_prompt = PromptTemplate(
            template=THREAD_SUMMARY_PROMPT_TEMPLATE,
            input_variables=["text"])

        self.refine_prompt = PromptTemplate(
            template=REFINE_PROMPT_TEMPLATE,
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

    def split_thread_data_into_chunks(self) -> Tuple[List[Document], List[int]]:
        chunk = ""
        chunks = []
        token_count_per_chunk = []

        for message in self.thread_data:
            chunk += message + "\n"
            token_count = self.llm.get_num_tokens(chunk)
            if token_count > self.max_tokens_per_chunk * .9:  # avoid spilling over token buffer to avoid warnings
                chunks.append(chunk)
                token_count_per_chunk.append(token_count)
                chunk = ""
        if chunk != "":
            chunks.append(chunk)
            token_count_per_chunk.append(token_count)

        return [Document(page_content=chunk) for chunk in chunks], token_count_per_chunk

    async def summarize(self) -> str:

        thread_as_string = "\n".join(self.thread_data)
        if len(thread_as_string) == 0:
            return "Thread is empty"

        total_token_count = self.llm.get_num_tokens(thread_as_string)
        thread_chunks, token_count_per_chunk = self.split_thread_data_into_chunks()
        chain = load_summarize_chain(self.llm,
                                     chain_type="refine",
                                     verbose=True,
                                     question_prompt=self.base_summary_prompt,
                                     refine_prompt=self.refine_prompt
                                     )

        print(f"Generating thread summary for thread with model {self.llm_model}. Thread: \n {thread_as_string}\n")
        print(f"Number of tokens in input: {total_token_count} tokens")
        print(f"Broken up into {len(thread_chunks)} chunks with token counts: {token_count_per_chunk}")
        print(f"Estimated cost of total input: ${total_token_count * self.dollars_per_token}")

        return await chain.arun(thread_chunks)


async def summarize_threads(server_name: str,
                            collection_name: str = None,
                            overwrite: bool = False,
                            save_to_json: bool = True):
    mongo_database = MongoDatabaseManager()
    if collection_name is None:
        collection_name = get_thread_backups_collection_name(server_name=server_name)

    thread_collection = mongo_database.get_collection(collection_name)
    logger.info("Generating thread summary")

    for document in thread_collection.find():
        if "summary" in document and not overwrite:
            logger.info("Skipping thread summary generation, already exists")
            continue
        thread_as_list_of_strings = document["thread_as_list_of_strings"]

        try:
            thread_summarizer = ThreadSummarizer(thread_data=thread_as_list_of_strings, use_anthropic=True)
            thread_summary = await thread_summarizer.summarize()
        except Exception as e:
            logger.error(f"Summary generation failed with error: {e}. Trying again with OpenAI API")
            thread_summarizer = ThreadSummarizer(thread_data=thread_as_list_of_strings, use_anthropic=False)
            thread_summary = await thread_summarizer.summarize()

        logger.info(f"Saving thread summary to mongo database, summary: {thread_summary}")

        print(f"Thread summary: {thread_summary}\n\n-----------------------------------\n\n")

        mongo_database.upsert(
            collection=get_thread_backups_collection_name(server_name=server_name),
            query=document,
            data={
                "$set": {
                    "summary": thread_summary
                }
            }
        )

    if save_to_json:
        mongo_database.save_json(collection_name=collection_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(summarize_threads(server_name="Neural Control of Real World Human Movement 2023 Summer1",
                                  overwrite=True,
                                  save_to_json=True))
