import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Union

from pymongo import MongoClient

from chatbot.system.environment_variables import get_mongo_uri, get_mongo_database_name
from chatbot.system.filenames_and_paths import get_default_database_json_save_path, \
    STUDENT_PROFILES_COLLECTION_NAME

logger = logging.getLogger(__name__)

TEST_MONGO_QUERY = {
    "student_id": "test_student",
    "student_name": "test_student_name",
    "thread_title": "test_thread_title",
    "thread_id": f"test_session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
}


def default_serialize(o: Any) -> str:
    if isinstance(o, datetime):
        return o.isoformat()
    elif hasattr(o, "__dict__"):
        return o.__dict__
    return str(o)


class MongoDatabaseManager:
    def __init__(self, mongo_uri: str = None):
        if mongo_uri is None:
            self._client = MongoClient(get_mongo_uri())
        else:
            self._client = MongoClient(mongo_uri)

        self._database = self._client.get_default_database(get_mongo_database_name())

    def get_collection(self, collection_name: str):
        if collection_name not in self._database.list_collection_names():
            self._database.create_collection(collection_name)
        return self._database[collection_name]

    def insert(self, collection: str, document: dict):
        return self._database[collection].insert_one(document)

    def upsert(self, collection: str, query: dict, data: dict):
        return self._database[collection].update_one(query, data, upsert=True)

    def find(self, collection_name: str, query: dict = None):
        query = query if query is not None else {}
        return self._database[collection_name].find(query)

    def save_json(self, collection_name: str, query: dict = None, save_path: Union[str, Path] = None):
        query = query if query is not None else defaultdict()
        collection = self._database[collection_name]
        save_path = save_path if save_path is not None else get_default_database_json_save_path(collection_name,
                                                                                                timestamp=True)
        data = list(collection.find(query))

        for document in data:
            document["_id"] = str(document["_id"])

        with open(save_path, 'w') as file:
            json.dump(data, file, indent=4, default=default_serialize)

        logger.info(f"Saved {len(data)} documents to {save_path}")

    def close(self):
        self._client.close()

    def get_student_profile(self, discord_username: str):
        return self._database[STUDENT_PROFILES_COLLECTION_NAME].find_one(
            {"discord_username": discord_username})

    def get_student_summary(self, discord_username: str):
        student_profile = self.get_student_profile(discord_username=discord_username)

        try:
            return student_profile["student_summary"]
        except Exception as e:
            logger.error(f"Error getting student summary for {discord_username}: {e}")
            return None


if __name__ == "__main__":
    MONGO_URI = 'mongodb://localhost:27017'  # run locally
    TEST_COLLECTION = 'test'
    mongodb_manager = MongoDatabaseManager(MONGO_URI)

    test_document = {
        'name': 'Test',
        'description': 'This is a test document',
        'timestamp': datetime.now(),
    }

    insert_result = mongodb_manager.insert(TEST_COLLECTION, test_document)
    print(f'Inserted document with ID: {insert_result.inserted_id}')

    find_result = mongodb_manager.find(TEST_COLLECTION)

    print("Documents in 'test' collection:")
    for document in find_result:
        print(document)

    mongodb_manager.save_json(TEST_COLLECTION)

    mongodb_manager._database.drop_collection(TEST_COLLECTION)

    mongodb_manager.close()

    print("Done!")
