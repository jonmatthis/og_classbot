from typing import List

from dotenv import load_dotenv
from langchain import PromptTemplate, LLMChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatAnthropic, ChatOpenAI
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from pydantic import BaseModel, Field

GRENE_CHECK_PARSER_PROMPT = """
Format this text: 

{input_text}

using these instructions: 

{format_instructions}

"""


class PaperSummary(BaseModel):
    citation: str = Field(description="The citation to the paper in APA format")
    abstract: str = Field(description="The abstract of the paper")
    summary: List[str] = Field(description="The summarized main points of the paper in a bulleted outline")
    tags: List[str] = Field(description="Tags formatted like #this-one using kebab-case-lowercase")



OUTPUT_FORMAT_INSTRUCTIONS = """
## Citation: 

[The citation to the paper in APA foramt]

## Abstract: 

[The abstract of the paper]

## Summary:

[A summary or overview of the major points of the paper]

## Tags

[Tags formatted liek #this-one using kebab-case-lowercase]

"""


class GreenCheckMessageParser:
    def __init__(self):
        load_dotenv()
        self._llm = ChatAnthropic(temperature=0,
                                  streaming=True,
                                  callbacks=[StreamingStdOutCallbackHandler()],
                                  )
        self._parser = PydanticOutputParser(pydantic_object=PaperSummary)
        self._output_fixing_parser = OutputFixingParser.from_llm(parser=self._parser, llm=self._llm)

        parse_input_prompt = PromptTemplate(
            template=GRENE_CHECK_PARSER_PROMPT,
            input_variables=["input_text"],
            partial_variables={"format_instructions": self._parser.get_format_instructions()}
        )

        self._parse_input_chain = LLMChain(llm=self._llm,
                                           prompt=parse_input_prompt,
                                           )


    def parse(self, input_text: str) -> PaperSummary:
        response = self._parse_input_chain.run(input_text=input_text)
        return self._parser.parse(response)

    async def aparse(self, input_text: str) -> PaperSummary:
        response = await self._parse_input_chain.arun(input_text=input_text)
        return self._parser.parse(response)
