#!/usr/bin/env python3
"""
测试网络连通性检查服务
"""

import socket
from unittest.mock import patch

from service.network_service import NetworkTester


def test_network_tester_returns_true_when_socket_connects():
    """socket 连接成功时返回 True，并透传 host/port/timeout。"""
    with patch("service.network_service.socket.create_connection") as create_connection:
        assert NetworkTester.test_connectivity("db.example", 5432, timeout=3) is True

    create_connection.assert_called_once_with(("db.example", 5432), timeout=3)


def test_network_tester_returns_false_for_timeout_and_socket_errors():
    """socket 超时或网络错误时返回 False。"""
    with patch(
        "service.network_service.socket.create_connection",
        side_effect=socket.timeout,
    ):
        assert NetworkTester.test_connectivity("db.example", 5432) is False

    with patch(
        "service.network_service.socket.create_connection",
        side_effect=OSError("connection refused"),
    ):
        assert NetworkTester.test_connectivity("db.example", 5432) is False
