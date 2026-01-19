import sys
import os
from core import (
    LanTransferClient, KeyBoard, format_time, clear_screen, draw_line,
    message_polling_worker, MessageNotifier, SelectableList,
    Colors, USE_COLORS, USE_KEYBOARD, latest_messages, message_lock,
    new_message_event, stop_event, Thread
)

# 界面类
class CLIInterface:
    current_ip = "127.0.0.1"
    current_port = 5000

    def __init__(self, client: LanTransferClient):
        self.client = client
        self.categories = ['images', 'documents', 'videos', 'audios', 'archives', 'others']
        self.category_names = {
            'images': '图片',
            'documents': '文档',
            'videos': '视频',
            'audios': '音频',
            'archives': '压缩包',
            'others': '其他'
        }
        self.category_icons = {
            'images': '🖼️', 'documents': '📄', 'videos': '🎬',
            'audios': '🎵', 'archives': '📦', 'others': '📁'
        }
        self.menu_items = [
            ('files', '📂 查看文件列表', '浏览文件'),
            ('upload', '⬆️ 上传文件', '上传文件'),
            ('download', '⬇️ 下载文件', '下载文件'),
            ('delete', '🗑️ 删除文件', '删除文件'),
            ('chat', '💬 消息频道', '进入聊天'),
            ('username', '👤 设置用户名', '设置用户名'),
            ('exit', '❌ 退出', '退出'),
        ]

    def print_banner(self):
        clear_screen()
        if USE_COLORS:
            print()
            print(Colors.BRIGHT_CYAN + '╔' + '═' * 48 + '╗' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '║' + Colors.RESET, end='')
            print(Colors.BOLD + Colors.BRIGHT_GREEN + '  🌐 LAN Transfer CLI Client  ' + Colors.RESET, end='')
            print(Colors.BRIGHT_CYAN + '║' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '╠' + '═' * 48 + '╣' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '║' + Colors.RESET, end='')
            print(Colors.info(f'  连接至: http://{self.client.server_ip}:{self.client.port}'), end='')
            padding = 48 - len(f'  连接至: http://{self.client.server_ip}:{self.client.port}')
            print(' ' * padding + Colors.BRIGHT_CYAN + '║' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '╚' + '═' * 48 + '╝' + Colors.RESET)
        else:
            print()
            print('=' * 50)
            print('     LAN Transfer CLI Client')
            print(f'     连接至: http://{self.client.server_ip}:{self.client.port}')
            print('=' * 50)
        print()

    def print_messages(self, messages: list, max_count: int = 13):
        print(Colors.header(' 📬 最近消息 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        if not messages:
            print(Colors.warning('   暂无消息'))
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            return
        for m in messages[-max_count:]:
            sender = m.get('sender', '匿名')
            content = m.get('content', '')
            t = format_time(m.get('timestamp', ''))
            if USE_COLORS:
                print(f' {Colors.info("[")}{t}{Colors.info("]")} {Colors.sender(sender)}: {content[:25]}')
            else:
                print(f' [{t}] {sender}: {content[:25]}')

        draw_line('─', 50, Colors.BRIGHT_BLUE)

    def main_menu(self):
        global latest_messages
        stop_event.clear()
        polling_thread = Thread(target=message_polling_worker, args=(self.client, 0.3), daemon=True)
        polling_thread.start()
        try:
            with message_lock:
                latest_messages = self.client.get_messages()
        except:
            latest_messages = []

        menu_list = SelectableList(
            [(action, name) for action, name, _ in self.menu_items],
            title="📋 功能菜单"
        )

        CLIInterface.current_ip = self.client.server_ip
        CLIInterface.current_port = self.client.port
        self._render_main_menu(menu_list)
        last_index = menu_list.selected_index
        last_message_count = len(latest_messages)
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_main_menu(menu_list)
                last_index = menu_list.selected_index
                last_message_count = len(latest_messages)
                continue
            key = KeyBoard.get_key()

            if key == 'UP':
                menu_list.selected_index = max(0, menu_list.selected_index - 1)
            elif key == 'DOWN':
                menu_list.selected_index = min(len(menu_list.items) - 1, menu_list.selected_index + 1)
            elif key == 'ENTER':
                action = menu_list.items[menu_list.selected_index][0]
                if action == 'exit':
                    stop_event.set()
                    print()
                    print(Colors.ok(' 再见! 👋 '))
                    print()
                    return
                elif action == 'chat':
                    self._run_chat_mode()
                    try:
                        with message_lock:
                            latest_messages = self.client.get_messages()
                    except:
                        pass
                    self._render_main_menu(menu_list)
                    last_index = menu_list.selected_index
                    last_message_count = len(latest_messages)
                else:
                    self._handle_action(action)
                    self._render_main_menu(menu_list)
                    last_index = menu_list.selected_index
                    last_message_count = len(latest_messages)
            elif key == 'ESC':
                stop_event.set()
                print()
                print(Colors.ok(' 再见! 👋 '))
                print()
                return
            elif key and key in '0123456789' and not USE_KEYBOARD:
                try:
                    idx = int(key) - 1
                    if 0 <= idx < len(menu_list.items):
                        action = menu_list.items[idx][0]
                        if action == 'exit':
                            stop_event.set()
                            return
                        elif action == 'chat':
                            self._run_chat_mode()
                            try:
                                with message_lock:
                                    latest_messages = self.client.get_messages()
                            except:
                                pass
                            self._render_main_menu(menu_list)
                            last_index = menu_list.selected_index
                            last_message_count = len(latest_messages)
                        else:
                            self._handle_action(action)
                            self._render_main_menu(menu_list)
                            last_index = menu_list.selected_index
                            last_message_count = len(latest_messages)
                except:
                    pass
            if menu_list.selected_index != last_index or len(latest_messages) != last_message_count:
                self._render_main_menu(menu_list)
                last_index = menu_list.selected_index
                last_message_count = len(latest_messages)

    def _render_main_menu(self, menu_list):
        self.print_banner()
        with message_lock:
            display_messages = latest_messages.copy()
        self.print_messages(display_messages)
        print()
        print(Colors.header(' 📋 功能菜单 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (action, name) in enumerate(menu_list.items):
            is_selected = i == menu_list.selected_index

            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{name}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{name}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 退出 '))
        sys.stdout.flush()

    def _run_chat_mode(self):
        global latest_messages
        scroll_offset = 0
        last_msg_count = 0
        self._render_chat_mode(scroll_offset)
        last_msg_count = len(latest_messages)
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                with message_lock:
                    current_count = len(latest_messages)
                if current_count > last_msg_count:
                    scroll_offset = 0
                last_msg_count = current_count
                self._render_chat_mode(scroll_offset)
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                with message_lock:
                    total = len(latest_messages)
                max_offset = max(0, total - 1)
                scroll_offset = min(max_offset, scroll_offset + 10)
                self._render_chat_mode(scroll_offset)
            elif key == 'DOWN':
                scroll_offset = max(0, scroll_offset - 10)
                self._render_chat_mode(scroll_offset)
            elif key == 'ESC' or key == 'q' or key == 'Q':
                return
            elif key == 'ENTER':
                new_message_event.clear()
                self._render_chat_mode_input()
                try:
                    with message_lock:
                        latest_messages = self.client.get_messages()
                        last_msg_count = len(latest_messages)
                except:
                    pass
                self._render_chat_mode(scroll_offset)
            with message_lock:
                current_count = len(latest_messages)
            if scroll_offset == 0 and current_count > last_msg_count:
                last_msg_count = current_count

    def _render_chat_mode(self, scroll_offset: int = 0):
        clear_screen()
        if USE_COLORS:
            print()
            print(Colors.BRIGHT_CYAN + '╔' + '═' * 48 + '╗' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '║' + Colors.RESET, end='')
            print(Colors.BOLD + Colors.BRIGHT_GREEN + '  💬 消息频道  ' + Colors.RESET, end='')
            print(Colors.BRIGHT_CYAN + '║' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '╠' + '═' * 48 + '╣' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '║' + Colors.RESET, end='')
            print(Colors.info(f'  用户: {self.client.sender_name}'), end='')
            padding = 48 - len(f'  用户: {self.client.sender_name}')
            print(' ' * padding + Colors.BRIGHT_CYAN + '║' + Colors.RESET)
            print(Colors.BRIGHT_CYAN + '╚' + '═' * 48 + '╝' + Colors.RESET)
        else:
            print()
            print('=' * 50)
            print('     💬 消息频道')
            print(f'     用户: {self.client.sender_name}')
            print('=' * 50)
        print()
        print(Colors.header(' 💬 消息记录 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        with message_lock:
            messages = latest_messages.copy()
        if not messages:
            print(Colors.warning('   暂无消息，开始聊天吧！'))
            draw_line('─', 50, Colors.BRIGHT_BLUE)
        else:
            total = len(messages)
            visible_count = 17
            start = max(0, total - 1 - scroll_offset)
            end = min(total, start + visible_count)
            visible_msgs = messages[start:end]
            if total > visible_count:
                if USE_COLORS:
                    print(f'   {Colors.info(f"显示 {start + 1}-{end} / 共 {total} 条 (↑↓ 滚动)")}')
                else:
                    print(f'   显示 {start + 1}-{end} / 共 {total} 条 (↑↓ 滚动)')
                draw_line('─', 50, Colors.BRIGHT_BLUE)
            for m in visible_msgs:
                sender = m.get('sender', '匿名')
                content = m.get('content', '')
                t = format_time(m.get('timestamp', ''))
                is_self = sender == self.client.sender_name
                if USE_COLORS:
                    if is_self:
                        print(f' {Colors.ok("[")}{t}{Colors.ok("]")} {Colors.ok("我")}: {content}')
                    else:
                        print(f' {Colors.timestamp("[")}{t}{Colors.timestamp("]")} {Colors.sender(sender)}: {content}')
                else:
                    marker = '(我)' if is_self else ''
                    print(f' [{t}] {sender}{marker}: {content}')
            draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        if USE_COLORS:
            print(Colors.BG_GREEN + Colors.BRIGHT_WHITE + ' 输入消息 (Enter 发送/开始输入消息, Esc/Q 返回) ' + Colors.RESET)
        else:
            print('=' * 50)
            print(' 输入消息 (Enter 发送/开始输入消息, Esc/Q 返回) ')
            print('=' * 50)
        sys.stdout.flush()

    def _render_chat_mode_input(self):
        if USE_COLORS:
            print(Colors.info(' > '), end='', flush=True)
        else:
            print(' > ', end='', flush=True)
        message = ""
        for char in KeyBoard.get_line():
            if char is None:
                print()
                break
            elif char == 'ESC':
                print()
                message = None
                break
            elif char == '\b':
                print('\b \b', end='', flush=True)
                if message:
                    message = message[:-1]
            else:
                message += char
                sys.stdout.write(char)
                sys.stdout.flush()
        if message and message.strip():
            result = self.client.send_message(message.strip())
            if result.get('success'):
                try:
                    with message_lock:
                        latest_messages = self.client.get_messages()
                except:
                    pass

    def _handle_action(self, action):
        if action == 'files':
            self._browse_files()
        elif action == 'upload':
            self._upload_file()
        elif action == 'download':
            self._download_file()
        elif action == 'delete':
            self._delete_file()
        elif action == 'username':
            self._set_username()

    def _browse_files(self):
        cat_list = [(cat, f'{self.category_icons.get(cat, "📁")} {self.category_names.get(cat, cat)}') for cat in self.categories]
        cat_list.append(('back', '🔙 返回主菜单'))
        selector = SelectableList(cat_list, title="📂 选择分类")
        self._render_category_select(selector)
        last_index = selector.selected_index
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_category_select(selector)
                last_index = selector.selected_index
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                value = selector.items[selector.selected_index][0]
                if value == 'back':
                    return
                self._show_category_files(value)
                selector.selected_index = 0
                self._render_category_select(selector)
                last_index = 0
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_category_select(selector)
                last_index = selector.selected_index

    def _render_category_select(self, selector):
        self.print_banner()
        print()
        print(Colors.header(' 📂 选择分类 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _show_category_files(self, category):
        files = self.client.get_files(category)
        cat_name = self.category_names.get(category, category)
        cat_icon = self.category_icons.get(category, '📁')
        if not files:
            self.print_banner()
            print()
            print(Colors.header(f' {cat_icon} {cat_name} '))
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            print()
            print(Colors.warning('   该分类下没有文件'))
            print()
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            print()
            print(Colors.info(' 按任意键返回... '))
            KeyBoard.get_key()
            return
        file_list = [(f['name'], f'{f["name"]} ({f["size"]})') for f in files]
        file_list.append(('back', '🔙 返回'))
        selector = SelectableList(file_list, title=f'{cat_icon} {cat_name}')
        self._render_file_list(selector, category)
        last_index = selector.selected_index
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_file_list(selector, category)
                last_index = selector.selected_index
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                value = selector.items[selector.selected_index][0]
                if value == 'back':
                    return
                self._show_file_detail(category, value)
                selector.selected_index = 0
                self._render_file_list(selector, category)
                last_index = 0
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_file_list(selector, category)
                last_index = selector.selected_index

    def _render_file_list(self, selector, category):
        self.print_banner()
        print()
        cat_name = self.category_names.get(category, category)
        cat_icon = self.category_icons.get(category, '📁')
        print(Colors.header(f' {cat_icon} {cat_name} '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _show_file_detail(self, category, filename):
        self.print_banner()
        print()
        print(Colors.header(f' 📄 文件详情 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(f'  文件名: {Colors.highlight(filename)}')
        print(f'  分类: {category}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' 按任意键返回... '))
        KeyBoard.get_key()

    def _upload_file(self):
        self.print_banner()
        print()
        print(Colors.header(' ⬆️ 上传文件 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print('  请输入文件路径')
        print()
        print(Colors.info(' 输入路径后按回车上传  |  输入 0 返回 '))
        print()
        file_path = input(f'  文件路径: ') if not USE_COLORS else \
            input(f'  {Colors.info("文件路径: ")}')
        if file_path == '0' or file_path == '':
            return
        if not os.path.exists(file_path):
            print()
            print(Colors.error('错误: 文件不存在'))
            print()
            print(Colors.info(' 按任意键返回... '))
            KeyBoard.get_key()
            return
        print()
        print(Colors.info('正在上传...'))
        print()

        def show_upload_progress(uploaded, total):
            percent = min(100, int(uploaded * 100 / total)) if total > 0 else 0
            bar_width = 30
            filled = int(bar_width * percent / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            if USE_COLORS:
                progress = f'  {Colors.BRIGHT_CYAN}{bar}{Colors.RESET} {percent:3d}% '
                progress += f'{Colors.info(self._format_size(uploaded))} / {self._format_size(total)}'
            else:
                progress = f'  [{bar}] {percent:3d}% {self._format_size(uploaded)} / {self._format_size(total)}'
            sys.stdout.write(f'\r{progress}')
            sys.stdout.flush()
        result = self.client.upload_file(file_path, progress_callback=show_upload_progress)
        sys.stdout.write('\r' + ' ' * 60 + '\r')
        sys.stdout.flush()
        print()
        if result.get('success'):
            file_name = result.get('file', {}).get('name', '')
            if file_name:
                print(Colors.ok('✓ 成功上传: ') + file_name)
            else:
                print(Colors.ok('✓ 上传成功!'))
        else:
            print(Colors.error('✗ 上传失败: ') + result.get('error', '未知错误'))
        print()
        print(Colors.info(' 按任意键继续... '))
        KeyBoard.get_key()

    def _download_file(self):
        cat_list = [(cat, f'{self.category_icons.get(cat, "📁")} {self.category_names.get(cat, cat)}') for cat in self.categories]
        cat_list.append(('back', '🔙 返回'))
        selector = SelectableList(cat_list, title="⬇️ 选择分类")
        self._render_download_select(selector)
        last_index = selector.selected_index
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_download_select(selector)
                last_index = selector.selected_index
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                value = selector.items[selector.selected_index][0]
                if value == 'back':
                    return
                self._download_from_category(value)
                selector.selected_index = 0
                self._render_download_select(selector)
                last_index = 0
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_download_select(selector)
                last_index = selector.selected_index

    def _render_download_select(self, selector):
        self.print_banner()
        print()
        print(Colors.header(' ⬇️ 选择分类 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _download_from_category(self, category):
        files = self.client.get_files(category)
        cat_name = self.category_names.get(category, category)
        cat_icon = self.category_icons.get(category, '📁')
        if not files:
            self.print_banner()
            print()
            print(Colors.header(f' {cat_icon} {cat_name} '))
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            print()
            print(Colors.warning('   该分类下没有文件'))
            print()
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            print()
            print(Colors.info(' 按任意键返回... '))
            KeyBoard.get_key()
            return
        file_list = [(f['name'], f'{f["name"]} ({f["size"]})') for f in files]
        file_list.append(('back', '🔙 返回'))
        selector = SelectableList(file_list, title="📥 选择文件")
        self._render_download_file_select(selector, category)
        last_index = selector.selected_index
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_download_file_select(selector, category)
                last_index = selector.selected_index
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                value = selector.items[selector.selected_index][0]
                if value == 'back':
                    return
                self._confirm_download(category, value)
                selector.selected_index = 0
                self._render_download_file_select(selector, category)
                last_index = 0
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_download_file_select(selector, category)
                last_index = selector.selected_index

    def _render_download_file_select(self, selector, category):
        self.print_banner()
        print()
        print(Colors.header(' 📥 选择文件 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _confirm_download(self, category, filename):
        self.print_banner()
        print()
        print(Colors.header(' 📥 确认下载 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(f'  文件: {Colors.highlight(filename)}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        confirm_list = [('yes', '✓ 确定下载'), ('no', '✗ 取消')]
        selector = SelectableList(confirm_list, title="请确认")
        self._render_confirm(selector)
        last_index = selector.selected_index
        while True:
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                if selector.selected_index == 0:
                    print()
                    print(Colors.info('正在下载...'))
                    print()
                    def show_progress(downloaded, total):
                        percent = min(100, int(downloaded * 100 / total)) if total > 0 else 0
                        bar_width = 30
                        filled = int(bar_width * percent / 100)
                        bar = '█' * filled + '░' * (bar_width - filled)
                        if USE_COLORS:
                            progress = f'  {Colors.BRIGHT_CYAN}{bar}{Colors.RESET} {percent:3d}% '
                            progress += f'{Colors.info(self._format_size(downloaded))} / {self._format_size(total)}'
                        else:
                            progress = f'  [{bar}] {percent:3d}% {self._format_size(downloaded)} / {self._format_size(total)}'
                        sys.stdout.write(f'\r{progress}')
                        sys.stdout.flush()
                    if self.client.download_file(category, filename, progress_callback=show_progress):
                        sys.stdout.write('\r' + ' ' * 60 + '\r')
                        sys.stdout.flush()
                        print()
                        print(Colors.ok('✓ 成功下载至: ') + filename)
                    else:
                        sys.stdout.write('\r' + ' ' * 60 + '\r')
                        sys.stdout.flush()
                        print()
                        print(Colors.error('✗ 下载失败'))
                return
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_confirm(selector)
                last_index = selector.selected_index

    # 格式化文件大小
    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f}{unit}'
            size /= 1024
        return f'{size:.1f}TB'

    def _render_confirm(self, selector):
        self.print_banner()
        print()
        print(Colors.header(' 📥 确认下载 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print('  按 Enter 确认下载')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                print(f'  {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _delete_file(self):
        cat_list = [(cat, f'{self.category_icons.get(cat, "📁")} {self.category_names.get(cat, cat)}') for cat in self.categories]
        cat_list.append(('back', '🔙 返回'))
        selector = SelectableList(cat_list, title="🗑️ 选择分类")
        self._render_delete_select(selector)
        last_index = selector.selected_index
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_delete_select(selector)
                last_index = selector.selected_index
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                value = selector.items[selector.selected_index][0]
                if value == 'back':
                    return
                self._delete_from_category(value)
                selector.selected_index = 0
                self._render_delete_select(selector)
                last_index = 0
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_delete_select(selector)
                last_index = selector.selected_index

    def _render_delete_select(self, selector):
        self.print_banner()
        print()
        print(Colors.header(' 🗑️ 选择分类 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _delete_from_category(self, category):
        files = self.client.get_files(category)
        cat_name = self.category_names.get(category, category)
        cat_icon = self.category_icons.get(category, '📁')
        if not files:
            self.print_banner()
            print()
            print(Colors.header(f' {cat_icon} {cat_name} '))
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            print()
            print(Colors.warning('   该分类下没有文件'))
            print()
            draw_line('─', 50, Colors.BRIGHT_BLUE)
            print()
            print(Colors.info(' 按任意键返回... '))
            KeyBoard.get_key()
            return
        file_list = [(f['name'], f'{f["name"]}') for f in files]
        file_list.append(('back', '🔙 返回'))
        selector = SelectableList(file_list, title="🗑️ 选择文件")
        self._render_delete_file_select(selector, category)
        last_index = selector.selected_index
        while True:
            if new_message_event.is_set():
                MessageNotifier.show_pending()
                self._render_delete_file_select(selector, category)
                last_index = selector.selected_index
                continue
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                value = selector.items[selector.selected_index][0]
                if value == 'back':
                    return
                self._confirm_delete(category, value)
                selector.selected_index = 0
                self._render_delete_file_select(selector, category)
                last_index = 0
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_delete_file_select(selector, category)
                last_index = selector.selected_index

    def _render_delete_file_select(self, selector, category):
        self.print_banner()
        print()
        print(Colors.header(' 🗑️ 选择文件 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                num_str = Colors.highlight(f'{i}.')
                print(f'  {num_str} {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {i}. {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _confirm_delete(self, category, filename):
        confirm_list = [('yes', '✓ 确定删除'), ('no', '✗ 取消')]
        selector = SelectableList(confirm_list, title=f"确认删除 {filename}?")
        self._render_delete_confirm(selector, filename)
        last_index = selector.selected_index
        while True:
            key = KeyBoard.get_key()
            if key == 'UP':
                selector.selected_index = max(0, selector.selected_index - 1)
            elif key == 'DOWN':
                selector.selected_index = min(len(selector.items) - 1, selector.selected_index + 1)
            elif key == 'ENTER':
                if selector.selected_index == 0:
                    result = self.client.delete_file(category, filename)
                    self.print_banner()
                    print()
                    if result.get('success'):
                        print(Colors.ok('✓ 删除成功'))
                    else:
                        print(Colors.error('✗ 删除失败: ') + result.get('error', '未知错误'))
                    print()
                    print(Colors.info(' 按任意键返回... '))
                    KeyBoard.get_key()
                return
            elif key == 'ESC':
                return
            if selector.selected_index != last_index:
                self._render_delete_confirm(selector, filename)
                last_index = selector.selected_index

    def _render_delete_confirm(self, selector, filename):
        self.print_banner()
        print()
        print(Colors.header(' 🗑️ 确认删除 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(f'  文件: {Colors.error(filename)}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        for i, (value, display) in enumerate(selector.items):
            is_selected = i == selector.selected_index
            if USE_COLORS:
                if is_selected:
                    prefix = Colors.selected(' ▶ ')
                else:
                    prefix = '   '
                print(f'  {prefix}{display}')
            else:
                prefix = '▶ ' if is_selected else '  '
                print(f'  {prefix}{display}')
        print()
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(Colors.info(' ↑↓ 选择  |  ↵ 确定  |  Esc 返回 '))

    def _set_username(self):
        self.print_banner()
        print()
        print(Colors.header(' 👤 设置用户名 '))
        draw_line('─', 50, Colors.BRIGHT_BLUE)
        print()
        print(f'当前用户名: {Colors.highlight(self.client.sender_name)}')
        print()
        name = input(f'  {Colors.info("请输入新用户名: ")}') if USE_COLORS else input('  请输入新用户名: ')
        if name:
            self.client.set_sender_name(name)
            print()
            print(Colors.ok('✓ 用户名已更新!'))
        else:
            print()
            print(Colors.warning('用户名不能为空'))
        print()
        print(Colors.info(' 按任意键继续... '))
        KeyBoard.get_key()
