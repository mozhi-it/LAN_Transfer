import sys
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime

# PyInstaller 打包支持
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.static_folder = os.path.join(BASE_DIR, 'static')
app.static_url_path = '/static'

# 配置
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {
    # 图片
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'ico',
    # 文档
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv',
    # 视频
    'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm',
    # 音频
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a',
    # 压缩包
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2',
}

# 文件分类映射
FILE_CATEGORIES = {
    'images': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'ico'],
    'documents': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv'],
    'videos': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
    'audios': ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a'],
    'archives': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'],
    'others': []
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB 最大文件

# 消息存储
messages = []
MAX_MESSAGES = 100


def get_category(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return 'others'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_time(timestamp):
    return datetime.fromisoformat(timestamp).strftime('%H:%M')


def get_file_info(filepath, filename):
    stat = os.stat(filepath)
    return {
        'name': filename,
        'size': format_size(stat.st_size),
        'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'category': get_category(filename)
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/files/<category>')
def list_files(category):
    if category not in FILE_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400

    folder = os.path.join(app.config['UPLOAD_FOLDER'], category)
    if not os.path.exists(folder):
        os.makedirs(folder)

    files = []
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            files.append(get_file_info(filepath, filename))

    files.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify({'files': files, 'category': category})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        category = get_category(file.filename)
        folder = os.path.join(app.config['UPLOAD_FOLDER'], category)
        if not os.path.exists(folder):
            os.makedirs(folder)

        filename = file.filename
        filepath = os.path.join(folder, filename)

        # 如果文件已存在，添加时间戳
        if os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            filepath = os.path.join(folder, filename)

        file.save(filepath)
        return jsonify({
            'success': True,
            'file': get_file_info(filepath, filename)
        })

    return jsonify({'error': 'File type not allowed'}), 400


@app.route('/api/download/<category>/<filename>')
def download_file(category, filename):
    if category not in FILE_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400

    folder = os.path.join(app.config['UPLOAD_FOLDER'], category)
    return send_from_directory(folder, filename, as_attachment=True)


@app.route('/api/delete/<category>/<filename>', methods=['DELETE'])
def delete_file(category, filename):
    if category not in FILE_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400

    folder = os.path.join(app.config['UPLOAD_FOLDER'], category)
    filepath = os.path.join(folder, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})

    return jsonify({'error': 'File not found'}), 404


# 消息相关API
@app.route('/api/messages')
def get_messages():
    return jsonify({'messages': messages[-50:]})  # 返回最近50条


@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'No content'}), 400

    content = data['content'].strip()
    if not content:
        return jsonify({'error': 'Empty message'}), 400

    sender = data.get('sender', 'Anonymous')
    message = {
        'id': len(messages) + 1,
        'sender': sender[:20],
        'content': content[:500],
        'timestamp': datetime.now().isoformat()
    }

    messages.append(message)
    if len(messages) > MAX_MESSAGES:
        messages.pop(0)

    return jsonify({'success': True, 'message': message})


@app.route('/api/stats')
def get_stats():
    stats = {}
    total_size = 0
    total_files = 0

    for category in FILE_CATEGORIES:
        folder = os.path.join(app.config['UPLOAD_FOLDER'], category)
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            stats[category] = len(files)
            total_files += len(files)
            for f in files:
                total_size += os.path.getsize(os.path.join(folder, f))

    return jsonify({
        'stats': stats,
        'total_files': total_files,
        'total_size': format_size(total_size)
    })


if __name__ == '__main__':
    import socket

    # 获取端口号
    port_input = input("请输入端口号 (默认 5000): ").strip()
    port = int(port_input) if port_input else 5000

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print(f"\n{'='*50}")
    print(f"  LAN Transfer Server Started")
    print(f"{'='*50}")
    print(f"  Network:  http://{local_ip}:{port}")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
