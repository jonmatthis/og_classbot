import os
from collections import defaultdict
import asyncio

from chatbot.bots.assistants.course_assistant.course_assistant import CourseAssistant
from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager


class RefactorBot:
    def __init__(self, directory: str, assistant):
        self.directory = directory
        self.assistant = assistant
        self.refactoring_to_do = defaultdict(dict)

    def get_python_files(self):
        python_files = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files

    async def check_style(self, file):
        with open(file, 'r') as f:
            file_content = f.read()

        # Send the content to the GPT-4 model
        issues = await self.assistant.async_process_input(file_content)

        return issues

    async def refactor(self):
        python_files = self.get_python_files()

        for file in python_files:
            issues = await self.check_style(file)
            if issues:
                self.refactoring_to_do[file] = issues

    def print_refactoring_to_do(self):
        for file, issues in self.refactoring_to_do.items():
            print(f"For file {file}, perform the following refactorings:")
            for issue in issues:
                print(issue)


if __name__ == "__main__":
    path_to_package = r"/chatbot/discord_bot"
    assistant = CourseAssistant()

    bot = RefactorBot(directory=path_to_package, assistant=assistant)
    asyncio.run(bot.refactor())
    bot.print_refactoring_to_do()
