// DOM 元素
const elements = {
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    filesList: document.getElementById('files-list'),
    categoryTabs: document.querySelectorAll('.tab-btn'),
    chatMessages: document.getElementById('chat-messages'),
    messageInput: document.getElementById('message-input'),
    sendBtn: document.getElementById('send-btn'),
    senderName: document.getElementById('sender-name'),
    toast: document.getElementById('toast'),
    serverAddress: document.getElementById('server-address'),
    totalFiles: document.getElementById('total-files'),
    totalSize: document.getElementById('total-size')
};

// 状态
let currentCategory = 'all';
let messageInterval = null;
let lastMessageId = 0;
let lastMessagesHtml = '';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initTabs();
    initChat();
    loadStats();
    loadMessages();
    updateServerAddress();
    startMessagePolling();
});

// 显示 Toast
function showToast(message, type = 'default', duration = 3000) {
    elements.toast.textContent = message;
    elements.toast.className = 'toast ' + type;
    elements.toast.classList.add('show');
    if (window.toastTimer) clearTimeout(window.toastTimer);
    window.toastTimer = setTimeout(() => {
        elements.toast.classList.remove('show');
    }, duration);
}

// 更新服务器地址
function updateServerAddress() {
    const protocols = window.location.protocol;
    const host = window.location.host;
    elements.serverAddress.textContent = `${protocols}//${host}`;
}

// 文件上传
function initUpload() {
    // 点击上传
    elements.uploadZone.addEventListener('click', () => {
        elements.fileInput.click();
    });

    elements.fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
        elements.fileInput.value = '';
    });

    // 拖拽上传
    elements.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.add('drag-over');
    });

    elements.uploadZone.addEventListener('dragleave', () => {
        elements.uploadZone.classList.remove('drag-over');
    });

    elements.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });
}

async function handleFiles(files) {
    const totalFiles = files.length;
    let completedFiles = 0;
    let successCount = 0;
    let failCount = 0;

    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const fileSize = formatFileSize(file.size);
        showToast(`正在上传: ${file.name} (${fileSize})`, 'default', 10000);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            completedFiles++;

            if (result.success) {
                successCount++;
                showToast(`✓ ${file.name}`, 'success', 2000);
            } else {
                failCount++;
                showToast(`✗ ${file.name}: ${result.error || '上传失败'}`, 'error', 3000);
            }

            // 全部完成时显示总结
            if (completedFiles === totalFiles) {
                loadStats();
                loadFiles();
                if (totalFiles > 1) {
                    showToast(`完成: ${successCount}个成功, ${failCount}个失败`, successCount > failCount ? 'success' : 'error');
                }
            }
        } catch (error) {
            completedFiles++;
            failCount++;
            showToast(`✗ ${file.name}: 网络错误`, 'error', 3000);
        }
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

// 文件分类切换
function initTabs() {
    elements.categoryTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            elements.categoryTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentCategory = tab.dataset.category;
            loadFiles();
        });
    });
}

// 加载文件列表
async function loadFiles() {
    try {
        const url = currentCategory === 'all'
            ? '/api/files/images'
            : `/api/files/${currentCategory}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.files) {
            renderFiles(data.files, data.category);
        }
    } catch (error) {
        console.error('加载文件失败:', error);
    }
}

async function loadAllFiles() {
    const categories = ['images', 'documents', 'videos', 'audios', 'archives', 'others'];
    let allFiles = [];

    for (const category of categories) {
        try {
            const response = await fetch(`/api/files/${category}`);
            const data = await response.json();
            if (data.files) {
                allFiles = allFiles.concat(data.files.map(f => ({...f, category})));
            }
        } catch (error) {
            console.error(`加载${category}失败:`, error);
        }
    }

    allFiles.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    renderFiles(allFiles, 'all');
}

function renderFiles(files, category) {
    if (currentCategory === 'all' && category !== 'all') {
        return;
    }

    if (files.length === 0) {
        elements.filesList.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                <p>暂无文件</p>
            </div>
        `;
        return;
    }

    elements.filesList.innerHTML = files.map(file => `
        <div class="file-item" data-category="${file.category}" data-filename="${file.name}">
            <div class="file-icon">
                ${getFileIcon(file.name)}
            </div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-meta">${file.size} · ${formatTime(file.timestamp)}</div>
            </div>
            <div class="file-actions">
                <button class="file-action-btn download" onclick="downloadFile('${file.category}', '${escapeHtml(file.name)}')" title="下载">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                </button>
                <button class="file-action-btn delete" onclick="deleteFile('${file.category}', '${escapeHtml(file.name)}')" title="删除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        // 图片
        png: '<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
        jpg: '<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
        jpeg: '<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
        gif: '<svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
        // 文档
        pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
        doc: '<svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        docx: '<svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        txt: '<svg viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        // 视频
        mp4: '<svg viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',
        avi: '<svg viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',
        // 音频
        mp3: '<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
        wav: '<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
        // 压缩
        zip: '<svg viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2"><path d="M21 8v13H3V8"/><path d="M23 3H1v5h22V3z"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
        rar: '<svg viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="2"><path d="M21 8v13H3V8"/><path d="M23 3H1v5h22V3z"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
    };

    return icons[ext] || '<svg viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>';
}

function downloadFile(category, filename) {
    window.location.href = `/api/download/${category}/${encodeURIComponent(filename)}`;
}

async function deleteFile(category, filename) {
    if (!confirm(`确定要删除 "${filename}" 吗？`)) return;

    try {
        const response = await fetch(`/api/delete/${category}/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showToast('删除成功', 'success');
            loadStats();
            loadFiles();
        } else {
            showToast(result.error || '删除失败', 'error');
        }
    } catch (error) {
        showToast('网络错误', 'error');
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return date.toLocaleDateString('zh-CN');
}

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        elements.totalFiles.textContent = data.total_files;
        elements.totalSize.textContent = data.total_size;
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 消息功能
function initChat() {
    // 发送消息
    const sendMessage = async () => {
        const content = elements.messageInput.value.trim();
        if (!content) return;

        const sender = elements.senderName.value.trim() || 'Anonymous';

        try {
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, sender })
            });

            const result = await response.json();

            if (result.success) {
                elements.messageInput.value = '';
                loadMessages();
            } else {
                showToast(result.error || '发送失败', 'error');
            }
        } catch (error) {
            showToast('网络错误', 'error');
        }
    };

    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // 加载历史消息
    loadMessages();
}

async function loadMessages() {
    try {
        const response = await fetch('/api/messages');
        const data = await response.json();

        if (data.messages) {
            renderMessagesDiff(data.messages);
        }
    } catch (error) {
        console.error('加载消息失败:', error);
    }
}

function renderMessagesDiff(messages) {
    const currentSender = elements.senderName.value.trim() || 'Anonymous';

    // 生成新消息HTML
    const newMessagesHtml = messages.map(msg => `
        <div class="message ${msg.sender === currentSender ? 'own' : 'other'}" data-id="${msg.id}">
            <div class="message-sender">${escapeHtml(msg.sender)}</div>
            <div class="message-content">${escapeHtml(msg.content)}</div>
            <div class="message-time">${formatMessageTime(msg.timestamp)}</div>
        </div>
    `).join('');

    // 如果消息数量变化或有新消息，只更新变化的部分
    const newLastId = messages.length > 0 ? messages[messages.length - 1].id : 0;

    if (messages.length === 0) {
        if (lastMessagesHtml !== '') {
            elements.chatMessages.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <p>暂无消息</p>
                </div>
            `;
            lastMessagesHtml = '';
        }
    } else if (lastMessageId === 0) {
        // 首次加载
        elements.chatMessages.innerHTML = newMessagesHtml;
        lastMessagesHtml = newMessagesHtml;
        lastMessageId = newLastId;
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    } else if (newLastId > lastMessageId) {
        // 有新消息，只追加新消息
        const newMessages = messages.filter(msg => msg.id > lastMessageId);
        const fragment = document.createDocumentFragment();

        newMessages.forEach(msg => {
            const div = document.createElement('div');
            div.className = `message ${msg.sender === currentSender ? 'own' : 'other'}`;
            div.dataset.id = msg.id;
            div.innerHTML = `
                <div class="message-sender">${escapeHtml(msg.sender)}</div>
                <div class="message-content">${escapeHtml(msg.content)}</div>
                <div class="message-time">${formatMessageTime(msg.timestamp)}</div>
            `;
            fragment.appendChild(div);
        });

        elements.chatMessages.appendChild(fragment);
        lastMessageId = newLastId;
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
    // 如果消息数量减少或相同，不做任何操作，避免闪烁
}

function formatMessageTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function startMessagePolling() {
    // 每3秒检查新消息
    messageInterval = setInterval(loadMessages, 3000);
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 初始加载
loadFiles();
