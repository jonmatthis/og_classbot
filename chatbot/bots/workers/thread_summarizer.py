from typing import List

from langchain import OpenAI, PromptTemplate, LLMChain


class ThreadSummarizer:
    def __init__(self,
                 thread_data: List[str]):
        self.thread_as_string = "\n".join(str(message) for message in thread_data)

        prompt = PromptTemplate(
            template="Provide an detailed summary of the following thread."
                     "(NOTE - Keep in mind that sometimes a conversation will involve a student trying to poke at the boundaries of the AI models's knowledge and security. In this case, we consider that as evidence of interest in AI and Large Language Models(llms)!"
                     ":\n\n{thread}"
                     "\n\nSUMMARY:",
            input_variables=["thread"])

        self.chain = LLMChain(llm=OpenAI(temperature=0),
                              prompt=prompt,
                              verbose=True)

    async def summarize(self) -> str:
        return await self.chain.arun(self.thread_as_string)
