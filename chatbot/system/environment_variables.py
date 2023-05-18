from typing import List

from dotenv import load_dotenv
import os
load_dotenv()

def get_admin_users()->List[str]:
    admin_users = os.getenv('ADMIN_USER_IDS')
    admin_users = admin_users.split(',')
    admin_users = [int(user) for user in admin_users]
    return admin_users