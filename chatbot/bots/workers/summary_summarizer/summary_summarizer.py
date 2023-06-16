import logging
import os

import tiktoken
from dotenv import load_dotenv
from langchain import LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.memory import ConversationBufferMemory
from langchain.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate

GENERIC_META_SUMMARY_PROMPT = """
I'm going to feed you one summary at a time and I want you to keep a running 'meta-summary' 
that captures the overall structure of the entries. 

Here is your current meta summary:
 
{current_meta_summary}
"""

load_dotenv()

logger = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

META_SUMMARY_PROMPTS = {
    "generic": GENERIC_META_SUMMARY_PROMPT}


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
            input_variables=["current_meta_summary"])

        human_message_prompt = HumanMessagePromptTemplate.from_template(
            template="Here's a new summary: {new_summary} update your current meta summary accordingly ",
            input_variables=["new_summary"]
        )
        return ChatPromptTemplate.from_messages(
            [system_message_prompt, human_message_prompt]
        )

    async def update_meta_summary_based_on_new_summary(self,
                                                       current_meta_summary: str,
                                                       new_summary: str,
                                                       ) -> str:
        return await self._llm_chain.arun(
            current_meta_summary=current_meta_summary,
            new_summary=new_summary,
        )


