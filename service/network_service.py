"""
网络服务模块
"""

import socket


class NetworkTester:
    """网络连接测试器"""

    @staticmethod
    def test_connectivity(host: str, port: int, timeout: int = 5) -> bool:
        """测试网络连接性"""
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True
        except (socket.timeout, socket.error, ConnectionRefusedError, OSError):
            return False
