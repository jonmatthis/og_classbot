from flask import Flask, jsonify

from chatbot.mongo_database.mongo_database_manager import MongoDatabaseManager
from chatbot.system.environment_variables import get_mongo_uri
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name


app = Flask(__name__)

mongodb_manager = MongoDatabaseManager(get_mongo_uri())

@app.route('/view', methods=['GET'])
def get_all_data():
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"

    collection_name = get_thread_backups_collection_name(server_name=server_name)
    output = []
    for s in mongodb_manager.find(collection_name):
        s['_id'] = str(s['_id'])  # Convert ObjectId to str for JSON serialization
        output.append(s)
    return jsonify({'result' : output})

if __name__ == '__main__':
    app.run(debug=True)
