import logging
import os

import tiktoken
from dotenv import load_dotenv
from langchain import LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.memory import ConversationBufferMemory
from langchain.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate

from chatbot.bots.workers.video_chatter_summary_builder.video_chatter_summary_builder_prompts import \
    VIDEO_CHATTER_SUMMARY_RESPONSE_SCHEMA, VIDEO_CHATTER_SCHEMATIZED_SUMMARY_SYSTEM_TEMPLATE, \
    VIDEO_CHATTER_NEW_SUMMARY_HUMAN_INPUT_PROMPT

GENERIC_META_SUMMARY_PROMPT = """
I will be showing you multiple summaries of the same thing. Your job is to update your current meta summary based on the new summary.

Here is your current meta summary:
 
{current_meta_summary}

The summaries will follow the following schema:

{response_schema}
  

"""

load_dotenv()

logger = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

META_SUMMARY_PROMPTS = {
    "generic": GENERIC_META_SUMMARY_PROMPT,
    "video_chatter": VIDEO_CHATTER_SCHEMATIZED_SUMMARY_SYSTEM_TEMPLATE,
}


class SummarySummarizer:
    def __init__(self,
                 use_anthropic: bool = False,
                 summary_type: str = "generic",
                 ):

        self.summary_type = summary_type
        self.summary_summarizer_prompt = self._create_chat_prompt()
        self._memory = ConversationBufferMemory()
        if use_anthropic:
            if os.getenv("ANTHROPIC_API_KEY") is None:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.llm = ChatAnthropic(temperature=0)
            self.llm_model = self.llm.model
            self.dollars_per_token = 0.00000163
        else:
            self.llm = ChatOpenAI(model_name='gpt-4',
                                  temperature=0,
                                  callbacks=[StreamingStdOutCallbackHandler()],
                                  streaming=True,
                                  )
            self.llm_model = self.llm.model_name
            self.dollars_per_token = 0.00003  # gpt-4

        self._llm_chain = LLMChain(llm=self.llm,
                                   prompt=self.summary_summarizer_prompt,
                                   # memory=self._memory,
                                   verbose=True,
                                   )

    def _create_chat_prompt(self):
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            template=META_SUMMARY_PROMPTS[self.summary_type],
            input_variables=["response_schema"])


        human_message_prompt = HumanMessagePromptTemplate.from_template(
            template= VIDEO_CHATTER_NEW_SUMMARY_HUMAN_INPUT_PROMPT,
            input_variables=["student_initials",
                             "new_conversation_summary",
                             "current_schematized_summary"]
        )
        return ChatPromptTemplate.from_messages(
            [system_message_prompt, human_message_prompt]
        )

    async def update_meta_summary_based_on_new_summary(self,
                                                       student_intials: str,
                                                       current_schematized_summary: str,
                                                       new_conversation_summary: str,
                                                       ) -> str:
        return await self._llm_chain.arun(
            student_initials=student_intials,
            current_schematized_summary=current_schematized_summary,
            response_schema=VIDEO_CHATTER_SUMMARY_RESPONSE_SCHEMA,
            new_conversation_summary=new_conversation_summary,
        )


