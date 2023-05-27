from typing import List

from langchain import OpenAI, PromptTemplate, LLMChain


class ThreadSummarizer:
    def __init__(self,
                 thread_data: List[str]):
        self.thread_as_string = "\n".join(str(message) for message in thread_data)

        prompt = PromptTemplate(
            template="Provide an extensive and detailed summary and analysis of the following thread. Pull out themes and topics, especially those related to the human's background and interests. "
                     ":\n\n{thread}"
                     "\n\nSUMMARY:",
            input_variables=["thread"])

        self.chain = LLMChain(llm=OpenAI(model_name="gpt-4",
                                         temperature=0,
                                         max_tokens=-1),
                              prompt=prompt,
                              verbose=True)

    async def summarize(self) -> str:
        return await self.chain.arun(self.thread_as_string)
