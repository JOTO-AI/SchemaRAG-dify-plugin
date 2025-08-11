"""
项目配置模块
"""

import os
from dataclasses import dataclass
from typing import Optional

# 尝试导入dotenv，如果失败则忽略。在生产环境中，通常使用环境变量。
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    load_dotenv = None


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """从环境变量中获取值"""
    return os.environ.get(key, default)


def get_env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    """从环境变量中获取整数值"""
    value = get_env(key)
    return int(value) if value is not None else default


@dataclass
class DatabaseConfig:
    """数据库连接配置"""

    type: str = get_env("DB_TYPE", "mysql")
    host: str = get_env("DB_HOST", "localhost")
    port: int = get_env_int("DB_PORT", 3306)
    user: str = get_env("DB_USER", "root")
    password: str = get_env("DB_PASSWORD", "password")
    database: str = get_env("DB_NAME")

    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        if self.type == "sqlite":
            return f"sqlite:///{self.database}"
        elif self.type == "postgresql":
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "mysql":
            return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "mssql":
            return f"mssql+pymssql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "oracle":
            return f"oracle+cx_Oracle://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        # 达梦
        elif self.type == "dameng":
            return f"dm+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.type}")


@dataclass
class LoggerConfig:
    """日志配置"""

    log_level: str = get_env("LOG_LEVEL", "INFO")
    log_file: Optional[str] = get_env("LOG_FILE", None)


@dataclass
class DifyUploadConfig:
    """Dify上传配置"""

    api_key: str = get_env("DIFY_API_KEY")
    base_url: str = get_env("DIFY_BASE_URL", "https://api.dify.ai/v1")
    indexing_technique: str = get_env("DIFY_INDEXING_TECHNIQUE", "high_quality")
    permission: str = get_env("DIFY_PERMISSION", "all_team_members")
    process_mode: str = get_env("DIFY_PROCESS_MODE", "custom")
    max_tokens: int = get_env_int("DIFY_MAX_TOKENS", 1000)
