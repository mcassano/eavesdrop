const chat = document.getElementById('chat');
const userList = document.getElementById('user-list');
const clientCount = document.getElementById('client-count');
const nicknameInput = document.getElementById('nickname');
const questionInput = document.getElementById('question');
const submitButton = document.getElementById('submit-question');
// Use current host for socket connection (works in both dev and production)
const socket = io(window.location.origin);

socket.on('message', function(message) {
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
        socket.emit('submit_question', { nickname, question });
        questionInput.value = '';
    }
});

questionInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        submitButton.click();
    }
});
