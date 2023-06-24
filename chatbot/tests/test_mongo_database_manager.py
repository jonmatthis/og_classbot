import os
import mongomock
import pytest

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager


# Set up fixture for MongoDB mock
@pytest.fixture(scope='function')
def mock_db_manager():
    mock_client = mongomock.MongoClient('mongodb://localhost:27017')
    os.environ['MONGO_URI_LOCAL'] = 'mongodb://localhost:27017'  # set environment variable
    os.environ['MONGODB_DATABASE_NAME'] = 'test_db'  # set environment variable
    db_manager = MongoDatabaseManager()
    db_manager._client = mock_client
    db_manager._database = mock_client[os.getenv('MONGODB_DATABASE_NAME')]
    return db_manager

def test_insert(mock_db_manager):
    test_document = {'name': 'Test', 'description': 'This is a test document'}
    result = mock_db_manager.insert('test', test_document)
    assert result.acknowledged
    assert result.inserted_id is not None

def test_upsert(mock_db_manager):
    test_document = {'name': 'Test', 'description': 'This is a test document'}
    result = mock_db_manager.upsert('test', {'name': 'Test'}, test_document)
    assert result.acknowledged

def test_find(mock_db_manager):
    test_document = {'name': 'Test', 'description': 'This is a test document'}
    mock_db_manager.insert('test', test_document)
    result = mock_db_manager.find('test', {'name': 'Test'})
    assert list(result) == [test_document]
