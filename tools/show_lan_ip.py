# -*- coding: utf-8 -*-
"""打印当前电脑的局域网 IPv4，供批处理调用。"""

import socket


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        print(sock.getsockname()[0])
    except OSError:
        try:
            print(socket.gethostbyname(socket.gethostname()))
        except OSError:
            print("127.0.0.1")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
