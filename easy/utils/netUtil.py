import platform
import socket


def get_local_ip():
    try:
        if platform.system().lower() == "windows":
            # localIP = socket.gethostbyname(socket.gethostname())
            localIP = [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        else:
            csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            csock.connect(('8.8.8.8', 80))
            (localIP, port) = csock.getsockname()
            csock.close()
    except socket.error:
        localIP = "127.0.0.1"
    return localIP
