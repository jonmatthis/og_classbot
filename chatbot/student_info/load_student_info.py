import csv
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

import discord
import pandas as pd
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_student_info()-> Dict[str, Any]:
    load_dotenv()
    student_info = {}
    with open(os.getenv('PATH_TO_STUDENT_INFO_CSV'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            student = {key: value for key, value in zip(header, row)}
            student_info[student["full_name"]] = student
    return student_info


def update_student_info(student_info: Dict[str, Any]):
    info_df = pd.DataFrame.from_dict(student_info, orient='index')
    csv_save_path = os.getenv('PATH_TO_STUDENT_INFO_CSV')
    Path(csv_save_path).parent.mkdir(parents=True, exist_ok=True)
    info_df.to_csv(csv_save_path, index=False)
    logger.info(f"Updated student info CSV file at {csv_save_path}")

    json_save_path = os.getenv('PATH_TO_STUDENT_INFO_JSON')
    Path(json_save_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_save_path, 'w') as f:
        json.dump(student_info, f, indent=4)


def find_student_discord_id(context: discord.ApplicationContext,
                            discord_username: str, ):
    server_members = list(context.guild.members)
    for member in server_members:
        if str(member) == discord_username:
            return member.id
        if f"{str(member)}" in discord_username.split('#')[0].lower()+"#0":
            return member.id
    print(f'Could not find a user with the username {discord_username}')



def add_discord_id_if_necessary(student_discord_id,
                                student_info:dict,
                                student_name:str):
    if student_name in student_info:
        if "discord_user_id" not in student_info[student_name] or student_info[student_name]['discord_user_id'] == '':
            student_info[student_name]['discord_user_id'] = str(student_discord_id)
            update_student_info(student_info)
        else:
            assert student_info[student_name]['discord_user_id'] == str(student_discord_id)

if __name__ == '__main__':
    print(load_student_info())
