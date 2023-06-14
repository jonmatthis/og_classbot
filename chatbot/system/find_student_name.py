def find_student_name(self, thread_owner_username):
    student_name = None
    student_discord_username = None

    for student_key, student_dict in self.student_info.items():
        if student_dict['discord_username'].split('#')[0].lower() == thread_owner_username.split('#')[0].lower():
            student_name = student_key
            student_discord_username = student_dict['discord_username']
            break
        if "other_discord_usernames" in student_dict:
            other_names = student_dict['other_discord_usernames'].split(',')
            if other_names[0] == '':
                continue
            for other_name in other_names:
                if other_name.split('#')[0].lower() == thread_owner_username.split('#')[0].lower():
                    student_name = student_key
                    student_discord_username = student_dict['discord_username']
                    break
    if student_name is None:
        student_name = "NOT_A_STUDENT"
        student_discord_username = thread_owner_username
    return {"student_discord_username": student_discord_username,
            "student_name": student_name}
