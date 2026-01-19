import sys
import os
import json
import threading
from datetime import datetime
from threading import Thread
try:
    import urllib.request
    import urllib.error
    import urllib.parse
except ImportError:
    import urllib2 as urllib_error
    import urlparse as urllib_parse
    import urllib2 as urllib_request


# 全局变量
latest_messages = []
message_lock = threading.Lock()
stop_event = threading.Event()
new_message_event = threading.Event()
pending_messages = []
USE_COLORS = None
USE_KEYBOARD = None


# 键盘输入处理
class KeyBoard:
    @staticmethod
    def is_available():
        return sys.platform != 'win32' or 'TERM' in os.environ

    @staticmethod
    def get_key():
        if sys.platform == 'win32':
            return KeyBoard._get_key_windows()
        else:
            return KeyBoard._get_key_unix()

    @staticmethod
    def _get_key_windows():
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch == b'\xe0':
                ch = msvcrt.getch()
                if ch == b'H':
                    return 'UP'
                elif ch == b'P':
                    return 'DOWN'
                elif ch == b'K':
                    return 'LEFT'
                elif ch == b'M':
                    return 'RIGHT'
            elif ch == b'\r':
                return 'ENTER'
            elif ch == b'\x08':
                return 'BACKSPACE'
            elif ch == b'\x1b':
                return 'ESC'
            else:
                try:
                    return ch.decode('gbk' if sys.platform == 'win32' else 'utf-8')
                except:
                    return ch.decode('latin-1')
        return None

    @staticmethod
    def _get_key_unix():
        import tty
        import termios
        import select

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    seq = sys.stdin.read(2)
                    if seq == '[A':
                        return 'UP'
                    elif seq == '[B':
                        return 'DOWN'
                    elif seq == '[C':
                        return 'RIGHT'
                    elif seq == '[D':
                        return 'LEFT'
                elif ch == '\r':
                    return 'ENTER'
                elif ch == '\x7f':
                    return 'BACKSPACE'
                elif ch == '\x1b':
                    return 'ESC'
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    @staticmethod
    def get_line():
        if sys.platform == 'win32':
            return KeyBoard._get_line_chars_windows()
        else:
            return KeyBoard._get_line_chars_unix()

    @staticmethod
    def _get_line_chars_windows():
        import msvcrt
        line = ""
        while True:
            ch = msvcrt.getch()
            if ch == b'\r':
                print()
                yield None
                break
            elif ch == b'\x08':
                if line:
                    line = line[:-1]
                    yield '\b'
            elif ch == b'\x1b':
                print()
                yield 'ESC'
                break
            else:
                try:
                    char = ch.decode('gbk')
                    line += char
                    yield char
                except:
                    pass

    @staticmethod
    def _get_line_chars_unix():
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            line = ""
            while True:
                ch = sys.stdin.read(1)
                if ch == '\r' or ch == '\n':
                    print()
                    yield None
                    break
                elif ch == '\x7f' or ch == '\x08':
                    if line:
                        line = line[:-1]
                        yield '\b'
                elif ch == '\x1b':
                    print()
                    yield 'ESC'
                    break
                else:
                    line += ch
                    yield ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

#  API客户端
class LanTransferClient:
    def __init__(self, server_ip: str, port: int = 5000):
        self.server_ip = server_ip
        self.port = port
        self.base_url = "http://{}:{}".format(server_ip, port)
        self.sender_name = "CLI用户"

    def set_sender_name(self, name: str):
        self.sender_name = name

    def _request(self, method: str, path: str, data: dict = None, files: tuple = None) -> dict:
        url = self.base_url + path
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            if files:
                boundary = '----WebKitFormBoundary' + str(datetime.now().timestamp())
                body = b''
                if data:
                    for key, value in data.items():
                        body += ('--' + boundary + '\r\n').encode()
                        body += ('Content-Disposition: form-data; name="' + key + '"\r\n\r\n').encode()
                        body += (value + '\r\n').encode()

                filename, file_content = files
                body += ('--' + boundary + '\r\n').encode()
                body += ('Content-Disposition: form-data; name="file"; filename="' + filename + '"\r\n').encode()
                body += b'Content-Type: application/octet-stream\r\n\r\n'
                body += file_content + b'\r\n'
                body += ('--' + boundary + '--\r\n').encode()

                headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
                req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            else:
                if data:
                    body = json.dumps(data).encode('utf-8')
                    headers['Content-Type'] = 'application/json'
                    req = urllib.request.Request(url, data=body, headers=headers, method=method)
                else:
                    req = urllib.request.Request(url, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=300) as response:
                content = response.read().decode('utf-8')
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {'raw': content}

        except urllib.error.HTTPError as e:
            try:
                error_content = e.read().decode('utf-8')
                return json.loads(error_content)
            except:
                return {'error': 'HTTP Error: ' + str(e.code)}
        except urllib.error.URLError as e:
            return {'error': '连接失败: ' + str(e.reason)}
        except Exception as e:
            return {'error': str(e)}

    def _get(self, path: str) -> dict:
        return self._request('GET', path)

    def _post(self, path: str, data: dict = None, files: tuple = None) -> dict:
        return self._request('POST', path, data=data, files=files)

    def _delete(self, path: str) -> dict:
        return self._request('DELETE', path)

    def get_files(self, category: str) -> list:
        result = self._get('/api/files/' + category)
        return result.get('files', []) if isinstance(result, dict) else []

    def upload_file(self, file_path: str, progress_callback=None) -> dict:
        if not os.path.exists(file_path):
            return {'error': '文件不存在'}
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            chunks = []
            read_bytes = 0
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    read_bytes += len(chunk)
                    if progress_callback and file_size > 0:
                        progress_callback(read_bytes, file_size)

            file_content = b''.join(chunks)
            result = self._post('/api/upload', files=(filename, file_content))
            return result if isinstance(result, dict) else {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def download_file(self, category: str, filename: str, save_path: str = None, progress_callback=None) -> bool:
        url = self.base_url + '/api/download/' + category + '/' + urllib.parse.quote(filename)
        try:
            save_path = save_path or filename
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                with open(save_path, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        downloaded += len(buffer)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
            return True
        except Exception:
            return False

    def delete_file(self, category: str, filename: str) -> dict:
        return self._delete('/api/delete/' + category + '/' + urllib.parse.quote(filename))

    def get_messages(self) -> list:
        result = self._get('/api/messages')
        return result.get('messages', []) if isinstance(result, dict) else []

    def send_message(self, content: str) -> dict:
        data = {'content': content, 'sender': self.sender_name}
        return self._post('/api/messages', data=data)

#  颜色定义
class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

    @staticmethod
    def ok(text):
        return Colors.GREEN + text + Colors.RESET

    @staticmethod
    def error(text):
        return Colors.RED + text + Colors.RESET

    @staticmethod
    def warning(text):
        return Colors.YELLOW + text + Colors.RESET

    @staticmethod
    def info(text):
        return Colors.CYAN + text + Colors.RESET

    @staticmethod
    def title(text):
        return Colors.BRIGHT_CYAN + Colors.BOLD + text + Colors.RESET

    @staticmethod
    def header(text):
        return Colors.BRIGHT_BLUE + Colors.BOLD + text + Colors.RESET

    @staticmethod
    def menu(text):
        return Colors.BRIGHT_WHITE + text + Colors.RESET

    @staticmethod
    def highlight(text):
        return Colors.BRIGHT_YELLOW + text + Colors.RESET

    @staticmethod
    def selected(text):
        return Colors.BG_GREEN + Colors.BRIGHT_WHITE + Colors.BOLD + text + Colors.RESET

    @staticmethod
    def sender(text):
        return Colors.BRIGHT_CYAN + Colors.BOLD + text + Colors.RESET

    @staticmethod
    def timestamp(text):
        return Colors.BRIGHT_BLACK + text + Colors.RESET

def supports_color():
    return sys.platform != 'win32' or 'TERM' in os.environ

def init_colors():
    global USE_COLORS, USE_KEYBOARD
    USE_COLORS = supports_color()
    USE_KEYBOARD = KeyBoard.is_available()

#  工具函数
def format_time(iso_time: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return iso_time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_line(char: str = '─', length: int = 50, color: str = ''):
    line = char * length
    if USE_COLORS and color:
        print(color + line + Colors.RESET)
    else:
        print(line)

#  消息轮询
def message_polling_worker(client: LanTransferClient, interval: float = 0.3):
    global latest_messages, pending_messages
    last_id = 0

    while not stop_event.is_set():
        try:
            messages = client.get_messages()
            if messages:
                new_last_id = messages[-1].get('id', 0)
                if new_last_id != last_id and last_id != 0:
                    new_msgs = [m for m in messages if m.get('id', 0) > last_id]
                    with message_lock:
                        latest_messages = messages
                        pending_messages.extend(new_msgs)
                    new_message_event.set()
                else:
                    with message_lock:
                        latest_messages = messages
                last_id = new_last_id
        except Exception:
            pass
        stop_event.wait(interval)

class MessageNotifier:
    @staticmethod
    def show_pending():
        global pending_messages
        if pending_messages:
            msg_list = pending_messages.copy()
            pending_messages.clear()
            new_message_event.clear()
            print()
            for m in msg_list:
                sender = m.get('sender', '匿名')
                content = m.get('content', '')
                t = format_time(m.get('timestamp', ''))

                if USE_COLORS:
                    msg = '\n' + Colors.BG_BLUE + ' ' * 50 + Colors.RESET + '\n'
                    msg += Colors.BG_BLUE + Colors.BRIGHT_WHITE + ' 💬 新消息 ' + Colors.RESET + '\n'
                    msg += Colors.BG_BLUE + ' ' * 50 + Colors.RESET + '\n'
                    msg += Colors.BG_BLUE + Colors.BRIGHT_WHITE + f'  [{t}] {sender}' + Colors.RESET + '\n'
                    msg += Colors.BG_BLUE + ' ' * 50 + Colors.RESET + '\n'
                    msg += Colors.BG_BLUE + Colors.BRIGHT_WHITE + f'  {content}' + Colors.RESET + '\n'
                    msg += Colors.BG_BLUE + ' ' * 50 + Colors.RESET + '\n'
                    sys.stdout.write(msg)
                else:
                    print()
                    print("=" * 50)
                    print(f" [新消息] [{t}] {sender}")
                    print(f" {content}")
                    print("=" * 50)
            sys.stdout.write('\n')

#  辅助类
class SelectableList:
    def __init__(self, items, title="", multi_select=False):
        self.items = items
        self.title = title
        self.multi_select = multi_select
        self.selected_index = 0
        self.selections = set() if multi_select else None
