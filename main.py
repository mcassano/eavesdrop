from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='.')
CORS(app)
socketio = SocketIO(app)

@app.route('/broadcast', methods=['POST'])
def broadcast_message():
    data = request.get_json()
    message = data['message']
    socketio.emit('message', message)
    return jsonify({"status": "success"}), 200

@app.route('/update_users', methods=['POST'])
def update_users():
    data = request.get_json()
    users = data['users']
    socketio.emit('update_users', users)
    return jsonify({"status": "success"}), 200

@app.route('/chatroom')
def serve_chatroom():
    return send_from_directory('.', 'chatroom.html')

@app.route('/chatroomjs')
def serve_chatroomjs():
    return send_from_directory('.', 'chatroom.js')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=os.getenv("PORT", default=5000))
