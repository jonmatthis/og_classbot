import os

from flask import Flask, jsonify
from flask_pymongo import PyMongo

from chatbot.system.environment_variables import get_mongo_uri
from chatbot.system.filenames_and_paths import get_thread_backups_collection_name

app = Flask(__name__)


app.config["MONGO_URI"] = get_mongo_uri()
mongo = PyMongo(app)

@app.route('/view', methods=['GET'])
def get_all_data():
    server_name = "Neural Control of Real World Human Movement 2023 Summer1"

    collection = mongo.db[get_thread_backups_collection_name(server_name=server_name)]
    output = []
    for s in collection.find():
        output.append({'_id' : str(s['_id']), 'data' : s['data']})  # Replace 'data' with your document fields
    return jsonify({'result' : output})

if __name__ == '__main__':
    app.run(debug=True)
