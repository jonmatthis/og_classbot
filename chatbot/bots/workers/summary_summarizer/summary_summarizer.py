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
    VIDEO_CHATTER_SUMMARY_RESPONSE_SCHEMA

GENERIC_META_SUMMARY_PROMPT = """
I will be showing you multiple summaries of the same video, as described by different people.

Your job is to create a comprehensive summary of the video, by combining the different summaries you see.

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
            input_variables=["current_meta_summary", "response_schema"])


        human_message_prompt = HumanMessagePromptTemplate.from_template(
            template="Here's a new summary:\n\n {new_summary} \n\n Update your current meta summary accordingly ",
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
            response_schema=VIDEO_CHATTER_SUMMARY_RESPONSE_SCHEMA,
            new_summary=new_summary,
        )


