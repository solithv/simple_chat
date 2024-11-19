let socket = null;
let currentRoom = null;

// ユーザー名を入力して接続を開始する
function connect() {
    const username = document.getElementById('username').value;
    if (!username) {
        alert("ユーザー名を入力してください。");
        return;
    }

    // Socket.IOの接続をユーザー名付きで確立
    socket = io('http://localhost:5000', {
        query: { name: username }
    });

    // 各種イベントリスナーの設定
    setupSocketListeners();

    // ユーザー名入力フォームを非表示にしてロビーを表示
    document.getElementById('username-form').style.display = 'none';
    document.getElementById('lobby').style.display = 'block';
}

// Socket.IOのイベントリスナーをセットアップ
function setupSocketListeners() {
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
        if (data.filename) addFile(data.user, data.filename, data.link);
    });
}

// ルームに参加
function joinRoom(roomName) {
    socket.emit('join', { room: roomName });
    currentRoom = roomName;
    document.getElementById('lobby').style.display = 'none';
    document.getElementById('chat').style.display = 'block';
    document.getElementById('room-name').textContent = `ルーム: ${roomName}`;
}

// 以下の関数は変更なし
function sendMessage() {
    const message = document.getElementById('message-input').value;
    if (message) {
        socket.emit('message', { message });
        document.getElementById('message-input').value = '';
    }
}

function sendImage() {
    const imageInput = document.getElementById('image-input');
    const file = imageInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = () => socket.emit('image', { image: reader.result });
        reader.readAsDataURL(file);
        imageInput.value = '';
    }
}

function sendFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    const reader = new FileReader();
    reader.onload = function (e) {
        socket.emit('file', {
            filename: file.name,
            file_data: e.target.result
        });
    };
    reader.readAsDataURL(file);
}

function createRoom() {
    const roomName = prompt("新しいルーム名を入力してください:");
    if (roomName) joinRoom(roomName);
}

function leaveRoom() {
    socket.emit('leave');
    document.getElementById('chat').style.display = 'none';
    document.getElementById('lobby').style.display = 'block';
}

function addMessage(user, message) {
    const chatLog = document.getElementById('chat-log');
    const messageItem = document.createElement('div');
    messageItem.textContent = `${user}: ${message}`;
    chatLog.appendChild(messageItem);
}

function addImage(user, imageData) {
    const chatLog = document.getElementById('chat-log');
    const imageItem = document.createElement('div');
    imageItem.innerHTML = `<strong>${user}</strong>: <img src="${imageData}" alt="image" style="max-width: 200px;">`;
    chatLog.appendChild(imageItem);
}

function addFile(user, fileName, link) {
    const chatLog = document.getElementById('chat-log');
    const fileItem = document.createElement('div');
    fileItem.innerHTML = `<strong>${user}</strong>: <a href="${link}" target="_blank">${fileName}</a>`;
    chatLog.appendChild(fileItem);
}