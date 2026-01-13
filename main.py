from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='.')
CORS(app)
socketio = SocketIO(app)

chat_history = []
user_list = []
connected_clients = 0
questions = []

MAX_CHAT_HISTORY = 200

@app.route('/broadcast', methods=['POST'])
def broadcast_message():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"status": "error", "message": "Missing 'message' field"}), 400

        message = str(data['message'])[:500]  # Sanitize and limit length
        chat_history.append(message)
        if len(chat_history) > MAX_CHAT_HISTORY:
            chat_history.pop(0)
        socketio.emit('message', message)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error in broadcast_message: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update_users', methods=['POST'])
def update_users():
    try:
        data = request.get_json()
        if not data or 'users' not in data:
            return jsonify({"status": "error", "message": "Missing 'users' field"}), 400

        users = data['users']
        # Validate and sanitize user list
        if not isinstance(users, list):
            return jsonify({"status": "error", "message": "Users must be a list"}), 400

        user_list.clear()
        user_list.extend([str(u)[:50] for u in users])  # Sanitize user names
        socketio.emit('update_users', user_list)
        return jsonify(user_list), 200  # Return the user list for GET requests
    except Exception as e:
        print(f"Error in update_users: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_questions', methods=['GET'])
def get_questions():
    try:
        global questions
        new_questions = questions[:]
        questions = []
        return jsonify(new_questions), 200
    except Exception as e:
        print(f"Error in get_questions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_chatroom():
    return send_from_directory('.', 'chatroom.html')

@app.route('/chatroomjs')
def serve_chatroomjs():
    return send_from_directory('.', 'chatroom.js')

@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients += 1
    print('Client connected')
    emit('chat_history', chat_history)
    emit('update_users', user_list)
    socketio.emit('update_client_count', connected_clients)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients
    connected_clients -= 1
    print('Client disconnected')
    socketio.emit('update_client_count', connected_clients)

@socketio.on('submit_question')
def handle_submit_question(data):
    try:
        nickname = str(data.get('nickname', 'Anonymous'))[:50]  # Sanitize
        question = str(data.get('question', ''))[:500]  # Sanitize and limit

        if not question.strip():
            return

        questions.append({'nickname': nickname, 'question': question})
        print(f"Received question from {nickname}: {question}")
    except Exception as e:
        print(f"Error handling question submission: {e}")

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=os.getenv("PORT", default=5000), allow_unsafe_werkzeug=True)
