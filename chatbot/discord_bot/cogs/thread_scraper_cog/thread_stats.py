import discord


class ThreadStats:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id

        self.stats = {
            "green_check_emoji_present": False,
            "thread_as_list_of_strings": [],
            "thread_as_one_string": "",

            "word_count_for_this_thread": {"total": 0, "student": 0, "bot": 0},
            "character_count_for_this_thread": {"total": 0, "student": 0, "bot": 0},
            "word_count_cumulative": {"total": [], "student": [], "bot": []}
        }

    def update(self, message: discord.Message):
        is_bot_user = message.author.id == self.bot_id
        message_author_str = str(message.author)

        message_content = message.content
        if message_content == '':
            return

        green_check_emoji_present_in_message = self.determine_if_green_check_present(message)
        if green_check_emoji_present_in_message:
            self.stats["green_check_emoji_present"] = True

        self.stats["thread_as_list_of_strings"].append(f"{message_author_str} said: '{message_content}'")

        message_word_count = len(message_content.split(' '))
        message_character_count = len(message_content)

        self.stats["word_count_for_this_thread"]["total"] += message_word_count
        self.stats["character_count_for_this_thread"]["total"] += message_character_count
        self.stats["word_count_cumulative"]["total"].append([message.created_at, self.stats["word_count_for_this_thread"]["total"]])

        if not is_bot_user:
            self.stats["word_count_for_this_thread"]["student"] += message_word_count
            self.stats["character_count_for_this_thread"]["student"] += message_character_count
            self.stats["word_count_cumulative"]["student"].append([message.created_at, self.stats["word_count_for_this_thread"]["student"]])
        else:
            self.stats["word_count_for_this_thread"]["bot"] += message_word_count
            self.stats["character_count_for_this_thread"]["bot"] += message_character_count
            self.stats["word_count_cumulative"]["bot"].append([message.created_at, self.stats["word_count_for_this_thread"]["bot"]])

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
        self.stats["thread_as_one_string"] = "\n".join(self.stats["thread_as_list_of_strings"])
        return self.stats
