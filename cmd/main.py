# LAN Transfer CLI Client
import sys
import os
import re

# 处理 PyInstaller 打包后的路径
if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
    os.chdir(base_path)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
if base_path not in sys.path:
    sys.path.insert(0, base_path)

from core import LanTransferClient, init_colors
from ui import CLIInterface


def main():
    # 初始化颜色支持
    from core import USE_COLORS, Colors
    init_colors()

    # 创建downloads文件夹
    download_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    os.chdir(download_dir)

    # 创建客户端
    client = LanTransferClient("127.0.0.1", 5000)
    interface = CLIInterface(client)
    print()
    print('=' * 50)
    print('     LAN Transfer CLI Client')
    print('     by MoZhi')
    print('=' * 50)
    print()
    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?::\d{1,5})?$'
    while True:
        ip = input(
            Colors.info('请输入服务器IP地址 ') +
            Colors.warning('(如 192.168.1.100:5000): ') +
            Colors.RESET
        ) if USE_COLORS else input('请输入服务器IP地址 (如 192.168.1.100:5000): ')

        if re.match(pattern, ip):
            break
        print(Colors.error('无效的IP地址格式，请重新输入'))
    if ':' in ip:
        server_ip, port = ip.rsplit(':', 1)
        port = int(port)
    else:
        server_ip = ip
        port = 5000
    client.server_ip = server_ip
    client.port = port
    client.base_url = "http://{}:{}".format(server_ip, port)
    print()
    print(Colors.info('正在连接服务器...'))

    try:
        messages = client.get_messages()
        print()
        print(Colors.ok('✓ 连接成功! ') + Colors.info('(消息实时接收中...)'))
        print()
        input(
            Colors.menu('按回车进入主菜单...') + Colors.RESET
        ) if USE_COLORS else input('按回车进入主菜单...')
    except Exception as e:
        print()
        print(Colors.error('✗ 连接失败: ') + str(e))
        print()
        input('按回车退出...')
        return

    interface.main_menu()

if __name__ == '__main__':
    main()
