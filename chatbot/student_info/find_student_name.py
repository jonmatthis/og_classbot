from chatbot.student_info.load_student_info import load_student_info


def find_student_info(thread_owner_username):
    student_name = None
    student_discord_username = None
    student_discord_id = None
    student_info = load_student_info()



    for student_key, student_dict in student_info.items():

        discord_usernames_to_check = find_user_names_to_check(student_dict)

        for discord_username_to_check in discord_usernames_to_check:
            if discord_username_to_check.lower() == thread_owner_username.lower() or\
                    discord_username_to_check.lower() in thread_owner_username.lower():
                student_name = student_key
                student_discord_username = student_dict['discord_username']
                student_discord_id = student_dict['discord_user_id']
                break



    known_exceptions = ["Jon#8343", "ProfJon#4002", "andreabuit519#2615"]
    if student_name is None:
        if thread_owner_username in known_exceptions:
            student_name = "NOT_A_STUDENT"
            student_discord_username = thread_owner_username
            student_discord_id = '000'
        else:
            raise ValueError(f"Could not find a student with the discord username {thread_owner_username}")

    return student_discord_username, student_name, student_discord_id


def find_user_names_to_check(student_dict):
    discord_usernames_to_check = [student_dict['discord_username']]
    if student_dict['other_discord_usernames'] != '':
        discord_usernames_to_check.extend(student_dict['other_discord_usernames'].split(','))
        discord_usernames_to_check = [discord_username.strip() for discord_username in discord_usernames_to_check]
    return discord_usernames_to_check
