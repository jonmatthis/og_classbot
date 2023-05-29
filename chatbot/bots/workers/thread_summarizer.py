import logging
import os
from datetime import datetime
from typing import List, Any, Dict

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

REFINE_THREAD_SUMMARY_PROMPT_TEMPLATE = """
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
    
    We have provided an existing summary of the thread up this point: 
    
    {existing_answer}
    
    Here is the next part of the conversation:
    ------------
    {text}
    ------------
    Given the new information, refine the original summary
    If the context isn't useful, return the original summary.
    
    In your answer do NOT include ANY:
     - pre-amble (such as "Here is the summary" or "The refined summary is"),
     - post-script (such as "Does this summary and recommendations seem accurate?" or  "Let me know if you have any other questions!")
    ...or any other text that is not part of the summary itself.
    
    Don't assume gender or pronouns. Use "they" or "them" instead of "he" or "she"
"""


def split_thread_data_into_chunks(messages: List[Any],
                                  max_tokens_per_chunk: int = 1000) -> List[Dict[str, Any]]:
    chunk = ""
    chunks = []
    token_count = 0
    for message in messages:
        chunk += message['content'] + "\n"
        token_count = OpenAI().get_num_tokens(chunk)
        if token_count > max_tokens_per_chunk * .9:  # avoid spilling over token buffer to avoid warnings
            chunks.append({"text": chunk,
                           "token_count": token_count, })
            chunk = message['content'] + "\n"  # overlap chunks by one message

    if chunk != "":
        chunks.append({"text": chunk,
                       "token_count": token_count, })
    return chunks


class ThreadSummarizer:
    def __init__(self,
                 use_anthropic: bool = False,
                 ):

        self.base_summary_prompt = PromptTemplate(
            template=THREAD_SUMMARY_PROMPT_TEMPLATE,
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
                                          chain_type="refine",
                                          verbose=True,
                                          question_prompt=self.base_summary_prompt,
                                          refine_prompt=self.refine_prompt,
                                          return_refine_steps=True,
                                          )

    async def summarize(self, thread_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        chunks_as_documents = [Document(page_content=chunk["text"]) for chunk in thread_chunks]
        if len(chunks_as_documents) >1:
            f=9
        summary = await self.chain.acall({"input_documents":chunks_as_documents}, return_only_outputs=True)
        return summary


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
                                  overwrite=True,
                                  save_to_json=True))
