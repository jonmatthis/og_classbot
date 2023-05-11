def test_mongodb_manager():
    mongodb_manager = MongoDBManager(os.getenv('MONGODB_URI'))

    test_document = {
        'name': 'Test',
        'description': 'This is a test document'
    }

    # Count the initial number of documents in the 'test' collection
    initial_count = mongodb_manager.find('test').count()

    # Insert the test document into a 'test' collection
    insert_result = mongodb_manager.insert('test', test_document)
    assert insert_result.acknowledged == True

    # Retrieve all documents from the 'test' collection
    find_result = mongodb_manager.find('test')

    # Ensure the number of documents has increased by one
    final_count = find_result.count()
    assert final_count == initial_count + 1
