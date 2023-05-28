from flask import Flask, jsonify
from flask_pymongo import PyMongo

app = Flask(__name__)

# You should replace "mongodb://localhost:27017/myDatabase" with your MongoDB URI and database name
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDatabase"
mongo = PyMongo(app)

@app.route('/view', methods=['GET'])
def get_all_data():
    collection = mongo.db.myCollection  # Replace "myCollection" with your collection name
    output = []
    for s in collection.find():
        output.append({'_id' : str(s['_id']), 'data' : s['data']})  # Replace 'data' with your document fields
    return jsonify({'result' : output})

if __name__ == '__main__':
    app.run(debug=True)
