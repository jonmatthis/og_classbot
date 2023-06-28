import discord


class ThreadStats:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self.thread_as_list_of_strings = []
        self.word_count_for_this_thread_total = 0
        self.word_count_for_this_thread_student = 0
        self.character_count_for_this_thread_total = 0
        self.character_count_for_this_thread_student = 0
        self.green_check_emoji_present_in_thread = False

    def update(self, message: discord.Message):
        is_bot_user = False
        if message.author.id == self.bot_id:
            is_bot_user = True
        message_author_str = str(message.author)

        message_content = message.content
        if message_content == '':
            return

        green_check_emoji_present_in_message = self.determine_if_green_check_present(message)
        if green_check_emoji_present_in_message:
            self.green_check_emoji_present_in_thread = True

        self.thread_as_list_of_strings.append(f"{message_author_str} said: '{message_content}'")

        message_word_count = len(message_content.split(' '))
        self.word_count_for_this_thread_total += message_word_count
        message_character_count = len(message_content)
        self.character_count_for_this_thread_total += message_character_count

        if message.author.id != is_bot_user:
            self.word_count_for_this_thread_student += message_word_count
            self.character_count_for_this_thread_student += message_character_count

    def determine_if_green_check_present(self, message: discord.Message):
        reactions = message.reactions
        green_check_emoji_present = False

        if len(reactions) > 0:
            for reaction in reactions:
                if reaction.emoji == '✅':
                    green_check_emoji_present = True
                    break

        if "Successfully sent summary" in message.content:
            green_check_emoji_present = False

        return green_check_emoji_present

    def to_dict(self):
        return {
            "thread_as_list_of_strings": self.thread_as_list_of_strings,
            "thread_as_one_string": "\n".join(self.thread_as_list_of_strings),
            "total_word_count_for_this_thread": self.word_count_for_this_thread_total,
            "word_count_for_this_thread_student": self.word_count_for_this_thread_student,
            "total_character_count_for_this_thread": self.character_count_for_this_thread_total,
            "character_count_for_this_thread_student": self.character_count_for_this_thread_student,
            "green_check_emoji_present": self.green_check_emoji_present_in_thread,
        }
