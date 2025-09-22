"""
工具模块
"""

import logging
from config import LoggerConfig

import datetime
import decimal
import re
import json


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def read_text(filename) -> str:
    data = []
    with open(filename, "r", encoding="utf-8") as file:
        for line in file.readlines():
            line = line.strip()
            data.append(line)
    return data


def save_raw_text(filename, content):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)


def read_map_file(path):
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip().split("\t")
            data[line[0]] = line[1].split("、")
            data[line[0]].append(line[0])
    return data


def save_json(target_file, js, indent=4):
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=indent)


def is_email(string):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    match = re.match(pattern, string)
    if match:
        return True
    else:
        return False


def examples_to_str(examples: list) -> list[str]:
    """
    from examples to a list of str
    """
    values = examples
    for i in range(len(values)):
        if isinstance(values[i], datetime.date):
            values = [values[i]]
            break
        elif isinstance(values[i], datetime.datetime):
            values = [values[i]]
            break
        elif isinstance(values[i], decimal.Decimal):
            values[i] = str(float(values[i]))
        elif is_email(str(values[i])):
            values = []
            break
        elif "http://" in str(values[i]) or "https://" in str(values[i]):
            values = []
            break
        elif values[i] is not None and not isinstance(values[i], str):
            pass
        elif values[i] is not None and ".com" in values[i]:
            pass

    return [str(v) for v in values if v is not None and len(str(v)) > 0]


class Logger:
    """日志管理器"""

    def __init__(self, config: LoggerConfig):
        self.config = config
        self._setup_logging()

    def _setup_logging(self):
        """设置日志配置"""
        handlers = [logging.StreamHandler()]

        # Only add FileHandler if log_file is not None
        # if self.config.log_file is not None:
        #     handlers.append(logging.FileHandler(self.config.log_file, encoding="utf-8"))

        # 将日志级别转换为大写，以匹配logging模块的常量
        log_level = self.config.log_level.upper()

        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
            force=True,
        )
        self.logger = logging.getLogger("dict_generator")

    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self.logger
