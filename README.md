# chatbot

Uses `discord.py` for the Discord stuff and `langchain` for the LLM stuff (mostly relying on OpenAI's `gpt-4` and Anthropic's `claude-v1` for the LLM stuff)

The bot's main AI brain lives in: `chatbot/ai/assistants/course_assistant`

It's main prompt is here: `chatbot/ai/assistants/course_assistant/prompts/general_course_assistant_prompt.py`

Summary data of a class deployed in Summer 2023 - `\chatbot\student_info\student_profiles\plots\html`
___

## Install
- make a python 3.10ish environment
- `pip install -e .`

## Run bot
- copy `sample.env` to `.env` and fill out the necessary info
- `python RUN_ME.py`

## Talk to bot
- with bot running, type `/chat` in any channel

## Scrape chat data
- with bot running, type `/scrape_threads` in any channel

## Process chat data
- see `chatbot/ai/workers` for examples
- anything with an `if __name__ == __main__:` block can be run without the discord bot being active


