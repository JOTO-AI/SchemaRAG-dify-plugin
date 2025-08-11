#!/usr/bin/env python3
"""
测试 SchemaRAG 构建过程的完整流程
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from unittest.mock import patch
from provider.build_schema_rag import SchemaRAGBuilderProvider
import logging

# 设置日志级别，减少不必要的输出
logging.basicConfig(level=logging.INFO)


def mock_dify_upload(dataset_name, schema_content):
    """模拟 Dify 上传过程"""
    print(f"🔄 模拟上传到 Dify 知识库: {dataset_name}")
    print(f"📄 Schema内容长度: {len(schema_content)} 字符")
    if schema_content:
        lines = schema_content.split("\n")
        table_count = len([line for line in lines if line.strip().startswith("# ")])
        print(f"📊 检测到 {table_count} 个表")
    return {"status": "success", "dataset_id": "mock_dataset_123"}


def test_schema_rag_build_process():
    """测试完整的 SchemaRAG 构建过程"""

    try:
        # 模拟插件配置
        test_credentials = {
            "api_uri": "http://localhost/v1",
            "dataset_api_key": "dataset-",
            "db_type": "mssql",
            "db_host": "localhost",
            "db_port": "1433",
            "db_user": "SA",
            "db_password": "Abcd%401234",
            "db_name": "test",
        }

        print("测试 SchemaRAG 构建过程:")
        print("=" * 80)

        # 创建 Provider 实例
        provider = SchemaRAGBuilderProvider()

        # 使用 Mock 来模拟 Dify 上传过程，避免实际网络请求
        with patch(
            "service.schema_builder.SchemaRAGBuilder.upload_text_to_dify",
            side_effect=mock_dify_upload,
        ):
            with patch(
                "service.schema_builder.SchemaRAGBuilder.close", return_value=None
            ):
                print("🚀 开始构建 Schema RAG...")

                # 执行构建过程
                try:
                    provider._build_schema_rag(test_credentials)
                    print("✅ Schema RAG 构建成功!")

                except Exception as e:
                    print(f"❌ Schema RAG 构建失败: {e}")
                    raise

        print("=" * 80)

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 开始 SchemaRAG 构建过程完整测试")
    print("=" * 80)

    try:
        # 1. 测试完整的构建过程（使用SQLite作为测试数据库）
        print("1️⃣ 测试完整的 Schema RAG 构建过程")
        test_schema_rag_build_process()

        print("\n🎉 所有测试完成!")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
