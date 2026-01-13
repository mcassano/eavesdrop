from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, that's okay
    pass

# Set timezone from environment variable
TIMEZONE = ZoneInfo(os.getenv("TZ", "America/Denver"))

app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/*": {"origins": "*"}})
# Configure Socket.IO with better timeout and ping settings
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    logger=False,  # Set to True for debugging
    engineio_logger=False,
    async_mode='threading'
)

chat_history = []
user_list = []
connected_clients = 0
questions = []

MAX_CHAT_HISTORY = 200

@app.route('/broadcast', methods=['POST'])
def broadcast_message():
    try:
        print(f'\n{"="*60}')
        print(f'[BROADCAST] HTTP /broadcast endpoint called')
        data = request.get_json()
        print(f'[BROADCAST] Received data: {data}')

        if not data or 'message' not in data:
            print(f'[BROADCAST] ERROR: Missing message field')
            return jsonify({"status": "error", "message": "Missing 'message' field"}), 400

        message = str(data['message'])[:500]  # Sanitize and limit length
        print(f'[BROADCAST] Message to broadcast: "{message[:100]}..."')

        chat_history.append(message)
        if len(chat_history) > MAX_CHAT_HISTORY:
            chat_history.pop(0)
        print(f'[BROADCAST] Added to chat_history (now has {len(chat_history)} messages)')

        try:
            print(f'[BROADCAST] Calling socketio.emit("message", ...)')
            print(f'[BROADCAST] Connected clients count: {connected_clients}')
            # Broadcast to all connected clients (broadcast is default when called from HTTP route)
            socketio.emit('message', message)
            print(f'[BROADCAST] ✅ socketio.emit() completed successfully')
        except Exception as e:
            print(f'[BROADCAST] ❌ Error in socketio.emit: {e}')
            import traceback
            traceback.print_exc()
        print(f'{"="*60}\n')
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"[BROADCAST] ❌ Error in broadcast_message: {e}")
        import traceback
        traceback.print_exc()
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
        try:
            socketio.emit('update_users', user_list)
        except Exception as e:
            print(f'Error broadcasting user list: {e}')
            import traceback
            traceback.print_exc()
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
    print(f'Client connected (total: {connected_clients})')
    try:
        emit('chat_history', chat_history)
        emit('update_users', user_list)
        emit('update_client_count', connected_clients, broadcast=True)
    except Exception as e:
        print(f'Error in handle_connect: {e}')
        import traceback
        traceback.print_exc()

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients
    connected_clients = max(0, connected_clients - 1)
    print(f'Client disconnected (total: {connected_clients})')
    try:
        emit('update_client_count', connected_clients, broadcast=True)
    except Exception as e:
        print(f'Error in handle_disconnect: {e}')

@socketio.on('submit_question')
def handle_submit_question(data):
    try:
        nickname = str(data.get('nickname', 'Anonymous'))[:50]  # Sanitize
        question = str(data.get('question', ''))[:500]  # Sanitize and limit

        if not question.strip():
            return

        # Store for test.py to process (but mark it so we don't duplicate)
        questions.append({'nickname': nickname, 'question': question, 'already_broadcast': True})
        
        # Immediately broadcast the message so user sees it right away
        current_time = datetime.now(TIMEZONE).strftime("%I:%M%p")
        formatted_message = f"{current_time} {nickname}: {question}"
        
        # Add to chat history
        chat_history.append(formatted_message)
        if len(chat_history) > MAX_CHAT_HISTORY:
            chat_history.pop(0)
        
        # Broadcast immediately via Socket.IO
        emit('message', formatted_message, broadcast=True)
        print(f"Received and broadcasted question from {nickname}: {question}")
    except Exception as e:
        print(f"Error handling question submission: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=os.getenv("PORT", default=5000), allow_unsafe_werkzeug=True)
