"""
Dify 插件日志辅助工具。
"""

import logging

from dify_plugin.config.logger_format import plugin_logger_handler


def configure_dify_tcp_logger() -> None:
    """避免 Dify TCP 写入失败时把内部 BrokenPipe 栈递归写回同一通道。"""
    tcp_logger = logging.getLogger("dify_plugin.core.server.tcp.request_reader")
    tcp_logger.propagate = False
    if not tcp_logger.handlers:
        tcp_logger.addHandler(logging.NullHandler())


def get_plugin_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取只写 Dify 插件日志通道的 logger，避免重复 handler 和根日志传播。"""
    configure_dify_tcp_logger()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if plugin_logger_handler not in logger.handlers:
        logger.addHandler(plugin_logger_handler)
    logger.propagate = False
    return logger
