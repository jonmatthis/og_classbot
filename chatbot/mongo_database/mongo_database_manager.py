import os
from datetime import datetime

from pymongo import MongoClient



class MongoDatabaseManager:
    def __init__(self):
        self._client = MongoClient(self.get_mongo_uri())
        self._database = self._client.get_default_database('chatbot')

    def get_mongo_uri(self)->str:
        is_docker = os.getenv('IS_DOCKER', False)
        if is_docker:
            return os.getenv('MONGO_URI_DOCKER')
        else:
            return os.getenv('MONGO_URI_LOCAL')

    def insert(self, collection, document):
        return self._database[collection].insert_one(document)

    def upsert(self, collection, query, data):
        return self._database[collection].update_one(query, data, upsert=True)

    def find(self, collection, query={}):
        return self._database[collection].find(query)


if __name__ == "__main__":
    # Replace 'your_mongodb_uri' with your actual MongoDB URI
    mongodb_manager = MongoDatabaseManager('mongodb://localhost:27017') #run locally

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
