"""
测试 Dify 插件日志保护配置。
"""

import logging

from dify_plugin.config.logger_format import plugin_logger_handler

from service.plugin_logging import configure_dify_tcp_logger, get_plugin_logger


def test_get_plugin_logger_adds_handler_once_and_disables_propagation():
    """业务 logger 应只挂一次插件 handler，避免重复写 TCP 通道。"""
    logger = get_plugin_logger("test.plugin.logger")
    before_count = logger.handlers.count(plugin_logger_handler)

    same_logger = get_plugin_logger("test.plugin.logger")
    after_count = same_logger.handlers.count(plugin_logger_handler)

    assert same_logger is logger
    assert before_count == 1
    assert after_count == 1
    assert logger.propagate is False


def test_configure_dify_tcp_logger_suppresses_recursive_internal_logging():
    """Dify TCP writer 内部 BrokenPipe 日志不应再写回同一个 stdout/TCP 通道。"""
    configure_dify_tcp_logger()

    tcp_logger = logging.getLogger("dify_plugin.core.server.tcp.request_reader")

    assert tcp_logger.propagate is False
    assert any(isinstance(handler, logging.NullHandler) for handler in tcp_logger.handlers)
