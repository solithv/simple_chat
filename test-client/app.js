const socket = io('http://localhost:5000');
let currentRoom = null;

// 初期接続でロビーのルーム一覧を取得
socket.on('connection', (data) => {
    const roomList = document.getElementById('room-list');
    roomList.innerHTML = "";
    data.rooms.forEach(room => {
        const listItem = document.createElement('li');
        listItem.textContent = `${room.name} (${room.count}人)`;
        listItem.onclick = () => joinRoom(room.name);
        roomList.appendChild(listItem);
    });
});

socket.on('error', (data) => {
    alert(data.message);
});

// ロビーのルーム一覧を取得
socket.on('rooms', (data) => {
    const roomList = document.getElementById('room-list');
    roomList.innerHTML = "";
    data.forEach(room => {
        const listItem = document.createElement('li');
        listItem.textContent = `${room.name} (${room.count}人)`;
        listItem.onclick = () => joinRoom(room.name);
        roomList.appendChild(listItem);
    });
});

// ユーザーの入室通知
socket.on('joined', (messages) => {
    document.getElementById('chat-log').innerHTML = "";
    messages.forEach(msg => addMessage(msg.user, msg.message));
});

// メッセージ受信
socket.on('message', (data) => {
    if (data.message) addMessage(data.user, data.message);
    if (data.image) addImage(data.user, data.image);
    if (data.file) addFile(data.user, data.file);
});

// メッセージ送信
function sendMessage() {
    const message = document.getElementById('message-input').value;
    if (message) {
        socket.emit('message', { message });
        document.getElementById('message-input').value = '';
    }
}

// 画像送信
function sendImage() {
    const imageInput = document.getElementById('image-input');
    const file = imageInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = () => socket.emit('message', { image: reader.result });
        reader.readAsDataURL(file);
        imageInput.value = '';
    }
}

// ファイル送信
function sendFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    if (file) {
        socket.emit('message', { file: file.name });
        fileInput.value = '';
    }
}

// ルームに参加
function joinRoom(roomName) {
    const username = document.getElementById('username').value;
    if (username) {
        socket.emit('join', { name: username, room: roomName });
        currentRoom = roomName;
        document.getElementById('lobby').style.display = 'none';
        document.getElementById('chat').style.display = 'block';
        document.getElementById('room-name').textContent = `ルーム: ${roomName}`;
    } else {
        alert("ユーザー名を入力してください。");
    }
}

// 新しいルームを作成
function createRoom() {
    const roomName = prompt("新しいルーム名を入力してください:");
    if (roomName) joinRoom(roomName);
}

// ルームを退出
function leaveRoom() {
    socket.emit('leave');
    document.getElementById('chat').style.display = 'none';
    document.getElementById('lobby').style.display = 'block';
}

// メッセージの表示
function addMessage(user, message) {
    const chatLog = document.getElementById('chat-log');
    const messageItem = document.createElement('div');
    messageItem.textContent = `${user}: ${message}`;
    chatLog.appendChild(messageItem);
}

// 画像の表示
function addImage(user, imageData) {
    const chatLog = document.getElementById('chat-log');
    const imageItem = document.createElement('div');
    imageItem.innerHTML = `<strong>${user}</strong>: <img src="${imageData}" alt="image" style="max-width: 200px;">`;
    chatLog.appendChild(imageItem);
}

// ファイルのリンク表示
function addFile(user, fileName) {
    const chatLog = document.getElementById('chat-log');
    const fileItem = document.createElement('div');
    fileItem.innerHTML = `<strong>${user}</strong>: <a href="/files/${fileName}" target="_blank">${fileName}</a>`;
    chatLog.appendChild(fileItem);
}
