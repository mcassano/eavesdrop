const chat = document.getElementById('chat');
const userList = document.getElementById('user-list');
const clientCount = document.getElementById('client-count');
const nicknameInput = document.getElementById('nickname');
const questionInput = document.getElementById('question');
const submitButton = document.getElementById('submit-question');
// Use current host for socket connection (works in both dev and production)
const socket = io(window.location.origin, {
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: Infinity,
    timeout: 20000,
    transports: ['websocket', 'polling']
});

// Connection event handlers
socket.on('connect', function() {
    console.log('✅ Connected to server');
    console.log('Socket ID:', socket.id);
});

socket.on('disconnect', function(reason) {
    console.log('❌ Disconnected from server:', reason);
});

socket.on('connect_error', function(error) {
    console.error('❌ Connection error:', error);
});

socket.on('reconnect', function(attemptNumber) {
    console.log('🔄 Reconnected after', attemptNumber, 'attempts');
});

socket.on('reconnect_attempt', function(attemptNumber) {
    console.log('🔄 Reconnection attempt', attemptNumber);
});

socket.on('reconnect_error', function(error) {
    console.error('❌ Reconnection error:', error);
});

socket.on('reconnect_failed', function() {
    console.error('❌ Reconnection failed - giving up');
});

socket.on('message', function(message) {
    console.log('Received message:', message);
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    chat.appendChild(messageElement);
    chat.scrollTop = chat.scrollHeight;
});

socket.on('update_users', function(users) {
    const userListDiv = document.getElementById('user-list');
    userListDiv.innerHTML = '';
    users.forEach(user => {
        const userDiv = document.createElement('div');
        userDiv.textContent = user;
        userListDiv.appendChild(userDiv);
    });
});

socket.on('chat_history', function(history) {
    chat.innerHTML = '';
    history.forEach(function(message) {
        const messageElement = document.createElement('div');
        messageElement.textContent = message;
        chat.appendChild(messageElement);
    });
    chat.scrollTop = chat.scrollHeight;
});

socket.on('update_client_count', function(count) {
    clientCount.textContent = `Connected clients: ${count}`;
});

submitButton.addEventListener('click', function() {
    const nickname = nicknameInput.value.trim();
    const question = questionInput.value.trim();
    if (nickname && question) {
        console.log('Sending message:', { nickname, question });
        socket.emit('submit_question', { nickname, question });
        questionInput.value = '';
    } else {
        console.log('Cannot send: nickname or question is empty');
    }
});

questionInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        submitButton.click();
    }
});
