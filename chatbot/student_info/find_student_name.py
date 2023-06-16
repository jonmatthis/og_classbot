from chatbot.student_info.load_student_info import load_student_info


def find_student_name( thread_owner_username):
    student_name = None
    student_discord_username = None
    student_info = load_student_info()



    for student_key, student_dict in student_info.items():

        discord_usernames_to_check = [student_dict['discord_username']]
        if student_dict['other_discord_usernames'] != '':
            discord_usernames_to_check.extend(student_dict['other_discord_usernames'].split(','))
            discord_usernames_to_check = [discord_username.strip() for discord_username in discord_usernames_to_check]

        for discord_username_to_check in discord_usernames_to_check:
            if discord_username_to_check.lower() == thread_owner_username.lower() or discord_username_to_check.lower() in thread_owner_username.lower():
                student_name = student_key
                student_discord_username = student_dict['discord_username']
                break



    known_exceptions = ["Jon#8343", "ProfJon#4002", "andreabuit519#2615"]
    if student_name is None:
        if thread_owner_username in known_exceptions:
            student_name = "NOT_A_STUDENT"
            student_discord_username = thread_owner_username
        else:
            raise ValueError(f"Could not find a student with the discord username {thread_owner_username}")

    return student_discord_username, student_name
