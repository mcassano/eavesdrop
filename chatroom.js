const chat = document.getElementById('chat');
const userList = document.getElementById('user-list');
const clientCount = document.getElementById('client-count');
const socket = io('https://www.eavesdrop.club');

socket.on('message', function(message) {
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    chat.appendChild(messageElement);
    chat.scrollTop = chat.scrollHeight;
});

socket.on('update_users', function(users) {
    userList.innerHTML = '';
    users.forEach(function(user) {
        const userElement = document.createElement('div');
        userElement.textContent = user;
        userList.appendChild(userElement);
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
