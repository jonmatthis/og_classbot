from typing import List

from dotenv import load_dotenv
from langchain import PromptTemplate, OpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class PaperSummary(BaseModel):
    citation: str = Field("", description="The citation to the research article")
    abstract: str = Field("", description="A copy-paste of the abstract of the research article")
    summary: str = Field("", description="A summary/overview of the major points of the paper in a bullet-point markdown format")
    tags: str = Field("", description="A list of tags formatted using #kebab-case-lowercase")

    def __str__(self):
        tags = "\n".join(self.tags)
        return f"""
                ## Citation:\n
                {self.citation}\n\n
                ## Abstract\n
                {self.abstract}\n\n
                ## Summary/overview\n
                {self.summary}\n\n
                ## Tags\n
                {tags}
                """



class GreenCheckMessageParser:
    def __init__(self):
        load_dotenv()
        self._llm = OpenAI(model_name="text-davinci-003",
                           temperature=0,
                            max_tokens=-1,
                           streaming=True,
                           callbacks=[StreamingStdOutCallbackHandler()],
                           )

        self._parser = PydanticOutputParser(pydantic_object=PaperSummary)

        self._prompt_template = PromptTemplate(
            template="Use these instructions to convert the input text into a paper summary:\n {format_instructions} \n\nInput text: \n___\n{input_text}\n\n___\nDO NOT MAKE ANYTHING UP. ONLY USE TEXT FROM THE INPUT TEXT. IF YOU DO NOT HAVE ENOUGH INFORMATION TO FILL OUT A FIELD SAY 'COULD NOT FIND IN INPUT TEXT'",
            input_variables=["input_text"],
            partial_variables={"format_instructions": self._parser.get_format_instructions()}
        )

    def parse_input(self, input_text: str) -> str:
        _input_text = self._prompt_template.format_prompt(input_text=input_text)
        _output = self._llm(_input_text.to_string())
        response = self._parser.parse(_output)
        return response

    async def aparse_input(self, input_text: str) -> str:
        response = self.parse_input(input_text=input_text)
        return response
