const chat = document.getElementById('chat');
const userList = document.getElementById('user-list');
const socket = io('http://localhost:5000');

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
