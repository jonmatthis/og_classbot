import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Union

from pymongo import MongoClient

from chatbot.system.environment_variables import get_mongo_uri, get_mongo_database_name, \
    get_mongo_chat_history_collection_name
from chatbot.system.filenames_and_paths import get_base_data_folder_path, get_default_json_save_path, \
    get_current_date_time_string

logger = logging.getLogger(__name__)

TEST_MONGO_QUERY = {"student_id": "test_student",
                    "student_name": "test_student_name",
                    "thread_title": "test_thread_title",
                    "thread_id": f"test_session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"}


class MongoDatabaseManager:
    def __init__(self, mongo_uri: str=None):
        if mongo_uri is None:
            self._client = MongoClient(get_mongo_uri())
        else:
            self._client = MongoClient(mongo_uri)

        self._database = self._client.get_default_database(get_mongo_database_name())

    @property
    def chat_history_collection(self):
        return self._database[get_mongo_chat_history_collection_name()]

    def get_collection(self, collection_name: str):
        if collection_name not in self._database.list_collection_names():
            self._database.create_collection(collection_name)
        return self._database[collection_name]

    def insert(self, collection, document):
        return self._database[collection].insert_one(document)

    def upsert(self, collection, query, data):
        return self._database[collection].update_one(query, data, upsert=True)

    def find(self, collection, query={}):
        return self._database[collection].find(query)

    def save_json(self, collection_name, query=None, save_path:Union[str, Path] = None):
        if query is None:
            query = defaultdict()
        collection = self._database[collection_name]
        if save_path is None:
            save_path = get_default_json_save_path(filename=f"{collection_name}_{get_current_date_time_string()}")

        # Convert the data to a list.
        data = list(collection.find(query))

        # Make sure the _id field (which is a MongoDB ObjectId) is serializable.
        for document in data:
            document["_id"] = str(document["_id"])

        # Save data to a JSON file.
        with open(save_path, 'w') as file:
            file.write(json.dumps(data, indent=4))

        logger.info(f"Saved {len(data)} documents to {save_path}")

if __name__ == "__main__":
    # Replace 'your_mongodb_uri' with your actual MongoDB URI
    mongodb_manager = MongoDatabaseManager('mongodb://localhost:27017')  # run locally

    test_document = {
        'name': 'Test',
        'description': 'This is a test document',
        'timestamp': datetime.now().isoformat(),
    }

    # Insert the test document into a 'test' collection
    insert_result = mongodb_manager.insert('test', test_document)
    print(f'Inserted document with ID: {insert_result.inserted_id}')

    # Retrieve all documents from the 'test' collection
    find_result = mongodb_manager.find('test')

    print("Documents in 'test' collection:")
    for document in find_result:
        print(document)

    mongodb_manager.save_json('test')

    # Delete the 'test' collection
    mongodb_manager._database.drop_collection('test')

    # Close the connection to MongoDB
    mongodb_manager._client.close()

    print("Done!")