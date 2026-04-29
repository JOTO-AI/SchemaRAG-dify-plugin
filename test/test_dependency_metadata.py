#!/usr/bin/env python3
"""
测试平台相关依赖声明
"""

import re
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestDependencyMetadata(unittest.TestCase):
    """依赖元数据测试"""

    def _read_pyproject(self) -> str:
        """读取 pyproject.toml 内容"""
        return (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    def _read_requirements(self) -> str:
        """读取 requirements.txt 内容"""
        return (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")

    def _find_dependency_line(self, package_name: str) -> str:
        """查找指定依赖声明行"""
        pattern = re.compile(
            rf'^\s*"({re.escape(package_name)}[^"]*)",',
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(self._read_pyproject())
        self.assertIsNotNone(match, f"未找到依赖声明: {package_name}")
        return match.group(1)

    def test_dameng_driver_dependencies_are_not_installed_on_macos(self):
        """达梦驱动依赖不应在 macOS 上安装"""
        for package_name in ("dmpython", "dmsqlalchemy"):
            dependency = self._find_dependency_line(package_name)

            self.assertIn("sys_platform", dependency)
            self.assertIn("linux", dependency)
            self.assertIn("win32", dependency)

            if sys.platform == "darwin":
                self.assertNotIn('sys_platform == "darwin"', dependency)

        requirements = self._read_requirements().lower()
        self.assertIn(
            'dmpython; sys_platform == "linux" or sys_platform == "win32"',
            requirements,
        )
        self.assertIn(
            'dmsqlalchemy; sys_platform == "linux" or sys_platform == "win32"',
            requirements,
        )

    def test_postgresql_uses_binary_driver_package(self):
        """PostgreSQL 依赖使用 binary 包避免本地编译 pg_config"""
        pyproject = self._read_pyproject().lower()

        self.assertIn("psycopg2-binary", pyproject)
        self.assertNotRegex(pyproject, r'"psycopg2[<>=,;\s"]')


if __name__ == "__main__":
    unittest.main()
