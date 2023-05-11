import asyncio
import logging
import sys
from pathlib import Path
from typing import Union

import toml
from langchain import OpenAI
from langchain.agents import AgentType, initialize_agent, load_tools
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory, ConversationSummaryMemory, \
    ConversationSummaryBufferMemory
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate, ChatPromptTemplate

from chatbot.langchain_stuff.agents.get_available_agents import get_agent_configuration

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv()


class Agent:
    def __init__(self,
                 configuration: dict = get_agent_configuration(),
                 config_path: Union[str, Path] = None,
                 model: str = None):

        if config_path is not None:
            try:
                self._configuration = toml.load(config_path)
            except Exception as e:
                logger.error(f"Could not load config TOML file at path: {config_path}")
                raise e
        else:
            self._configuration = configuration

        if model is not None:
            self._configuration["llm"]["model"] = model

        self._llm = self._configure_llm(**self._configuration["llm"], verbose=True)
        self._chat_prompt = self._create_chat_prompt()
        self._memory = self._configure_memory()
        self._agent = self._configure_agent()
        self._tools = self._configure_tools()

        # self._llm_chain = LLMChain(llm=self._llm,
        #                            prompt=self._chat_prompt,
        #                            memory=self._memory,
        #                            verbose=True)
        self._agent_chain = initialize_agent(tools=self._tools,
                                             llm=self._llm,
                                             agent=self._agent,
                                             memory=self._memory,
                                             verbose=True, )

    def intake_message(self, message: str):
        logger.info(f"Received message: {message}")
        return self._agent_chain.run(input=message)
        # return self._llm_chain.run(human_input=message, **self._prompt_input_variables)

    async def aintake_message(self, message: str):
        logger.info(f"Received message: {message}")
        return await self._agent_chain.arun(input=message)
        # return await self._llm_chain.arun(human_input=message, **self._prompt_input_variables)

    def _configure_llm(self,
                       type: str = "ChatOpenAI",
                       **kwargs):
        if type == "ChatOpenAI":
            if "streaming" in kwargs:
                if kwargs["streaming"]:
                    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
                    llm = ChatOpenAI(callbacks=[StreamingStdOutCallbackHandler()], **kwargs)
            else:
                llm = ChatOpenAI(**kwargs)

        return llm

    def _create_chat_prompt(self, prompt_config: dict = None, chat_prompt: bool = True):

        if not chat_prompt:
            raise Exception("non-chat prompts not yet implemented")

        if prompt_config is None:
            prompt_config = self._configuration["prompt"]

        if "input_variables" not in prompt_config:
            prompt_config["input_variables"] = {}

        self._prompt_input_variables = prompt_config["input_variables"]

        self._system_prompt = SystemMessagePromptTemplate.from_template(
            template=prompt_config["system_message_template"],
            input_variables=list(self._prompt_input_variables.keys())
        )
        self._system_prompt.format_messages(**self._prompt_input_variables)

        self._human_message_prompt = HumanMessagePromptTemplate.from_template(
            template=prompt_config["human_message_template"],
            input_variables=prompt_config["human_input_key"])

        return ChatPromptTemplate.from_messages([self._system_prompt, self._human_message_prompt])

    def _configure_memory(self):
        memory_config = self._configuration["memory"]
        logger.info(f"Configuring memory of type {memory_config}")

        if memory_config["type"] == "ConversationBufferMemory":
            memory = ConversationBufferMemory(memory_key=memory_config["memory_key"],
                                              return_messages=memory_config["return_messages"])

        elif memory_config["type"] == "ConversationBufferWindowMemory":
            memory = ConversationBufferWindowMemory(memory_key=memory_config["memory_key"],
                                                    return_messages=memory_config["return_messages"])

        elif memory_config["type"] == "ConversationSummaryMemory":
            memory = ConversationSummaryMemory(llm=self._configure_llm(model="gpt-3.5-turbo", temperature=0),
                                               memory_key=memory_config["memory_key"],
                                               return_messages=memory_config["return_messages"])
        elif memory_config["type"] == "ConversationSummaryBufferMemory":
            memory = ConversationSummaryBufferMemory(llm=self._configure_llm(model="gpt-3.5-turbo", temperature=0),
                                                     memory_key=memory_config["memory_key"],
                                                     return_messages=memory_config["return_messages"],
                                                     )
        else:
            raise NotImplementedError(f"Memory type {memory_config['type']} not implemented... YET!")

        return memory

    def _configure_agent(self):
        agent_config = self._configuration["agent"]
        logger.info(f"Configuring agent of type {agent_config}")

        if agent_config["type"] == "CHAT_CONVERSATIONAL_REACT_DESCRIPTION":
            return AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION

    def _configure_tools(self):
        math_llm = OpenAI(temperature=0.0)
        try:
            tools = load_tools(
                ["human", "llm-math"],
                llm=math_llm,
            )
        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            raise e

        return tools


async def ademo_main():
    agent = Agent()
    human_message_1 = "Hello, I am a human. I am here to talk to you about the weather."
    print(f"\n--Human says: {human_message_1}")
    print(await agent.aintake_message(human_message_1))
    human_message_2 = "Thats wild, tell me more!"
    print(f"\n--Human says: {human_message_2}")
    print(await agent.aintake_message(human_message_2))
    print("\n--Done!")


def demo_main():
    agent = Agent()
    human_message_1 = "Hello, I am a human. I am here to talk to you about the weather."
    print(f"\n--Human says: {human_message_1}")
    print(agent.intake_message(human_message_1))
    human_message_2 = "Thats wild, tell me more!"
    print(f"\n--Human says: {human_message_2}")
    print(agent.intake_message(human_message_2))
    print("\n--Done!")


if __name__ == "__main__":
    # Set the event loop policy to WindowsSelectorEventLoopPolicy on Windows
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        demo_main()
    except Exception as e:
        logger.error(f"Demo failed with exception: {e}")
        raise e

    print("\n--Demo ran successfully!")
