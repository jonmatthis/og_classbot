import csv
import logging
import os
from typing import Dict, Any

import pandas as pd
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_student_info():
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
    save_path = os.getenv('PATH_TO_STUDENT_INFO_CSV').replace('\\', '/')
    info_df.to_csv(save_path, index=False)
    logger.info(f"Updated student info CSV file at {save_path}")


if __name__ == '__main__':
    # csv schema
    # student_count,	email,	full_name,	sis_id,	discord_username,	github_username,
    # 1,	j.goodall@apesrgreat.com, Jane Goodall,	00123456789,	j.goodall#1234,	jgoodall,
    print(load_student_info())
