"""
上下文管理器测试

测试多轮对话记忆功能
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from service.context import ContextManager, Conversation, UserContext


def test_basic_context_operations():
    """测试基本的上下文操作"""
    print("=" * 50)
    print("测试基本上下文操作")
    print("=" * 50)
    
    # 创建上下文管理器
    cm = ContextManager()
    
    # 测试用户ID
    test_user_id = "test_user_123"
    
    # 添加几轮对话
    cm.add_conversation(
        query="查询所有用户",
        sql="SELECT * FROM users",
        user_id=test_user_id,
        metadata={"dialect": "mysql"}
    )
    
    cm.add_conversation(
        query="查询上个月的订单",
        sql="SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)",
        user_id=test_user_id,
        metadata={"dialect": "mysql"}
    )
    
    cm.add_conversation(
        query="按区域统计",
        sql="SELECT region, COUNT(*) FROM orders GROUP BY region",
        user_id=test_user_id,
        metadata={"dialect": "mysql"}
    )
    
    print(f"\n✓ 成功添加3轮对话")
    
    # 获取对话历史（窗口大小为2）
    history = cm.get_conversation_history(user_id=test_user_id, window_size=2)
    
    print(f"\n✓ 获取最近2轮对话:")
    for i, conv in enumerate(history, 1):
        print(f"  {i}. 问题: {conv['query']}")
        print(f"     SQL: {conv['sql'][:50]}...")
    
    # 获取所有历史
    full_history = cm.get_conversation_history(user_id=test_user_id, window_size=10)
    print(f"\n✓ 当前共有 {len(full_history)} 轮对话")
    
    # 重置记忆
    cm.reset_memory(user_id=test_user_id)
    print(f"\n✓ 已重置用户记忆")
    
    # 验证重置后的历史
    after_reset = cm.get_conversation_history(user_id=test_user_id, window_size=10)
    print(f"✓ 重置后对话数量: {len(after_reset)}")
    
    assert len(after_reset) == 0, "重置后应该没有对话历史"
    
    print("\n" + "=" * 50)
    print("✓ 所有基本测试通过！")
    print("=" * 50)


def test_multiple_users():
    """测试多用户隔离"""
    print("\n" + "=" * 50)
    print("测试多用户上下文隔离")
    print("=" * 50)
    
    cm = ContextManager()
    
    # 用户A的对话
    cm.add_conversation(
        query="用户A的问题1",
        sql="SELECT * FROM table_a",
        user_id="user_a"
    )
    
    cm.add_conversation(
        query="用户A的问题2",
        sql="SELECT * FROM table_a WHERE id > 10",
        user_id="user_a"
    )
    
    # 用户B的对话
    cm.add_conversation(
        query="用户B的问题1",
        sql="SELECT * FROM table_b",
        user_id="user_b"
    )
    
    # 获取各用户的历史
    history_a = cm.get_conversation_history(user_id="user_a")
    history_b = cm.get_conversation_history(user_id="user_b")
    
    print(f"\n✓ 用户A有 {len(history_a)} 轮对话")
    print(f"✓ 用户B有 {len(history_b)} 轮对话")
    
    assert len(history_a) == 2, "用户A应该有2轮对话"
    assert len(history_b) == 1, "用户B应该有1轮对话"
    
    print("\n" + "=" * 50)
    print("✓ 多用户隔离测试通过！")
    print("=" * 50)


def test_window_size():
    """测试记忆窗口大小"""
    print("\n" + "=" * 50)
    print("测试记忆窗口大小")
    print("=" * 50)
    
    cm = ContextManager()
    user_id = "window_test_user"
    
    # 添加10轮对话
    for i in range(1, 11):
        cm.add_conversation(
            query=f"问题 {i}",
            sql=f"SELECT * FROM table{i}",
            user_id=user_id
        )
    
    print(f"\n✓ 添加了10轮对话")
    
    # 测试不同窗口大小
    for window_size in [1, 3, 5, 10]:
        history = cm.get_conversation_history(user_id=user_id, window_size=window_size)
        print(f"✓ 窗口大小 {window_size}: 获取到 {len(history)} 轮对话")
        assert len(history) == window_size, f"窗口大小{window_size}应该返回{window_size}轮对话"
    
    print("\n" + "=" * 50)
    print("✓ 窗口大小测试通过！")
    print("=" * 50)


def test_conversation_model():
    """测试对话数据模型"""
    print("\n" + "=" * 50)
    print("测试对话数据模型")
    print("=" * 50)
    
    # 创建对话
    conv = Conversation(
        query="测试问题",
        sql="SELECT * FROM test",
        metadata={"dialect": "mysql", "dataset_id": "test_dataset"}
    )
    
    print(f"\n✓ 创建对话对象")
    print(f"  问题: {conv.query}")
    print(f"  SQL: {conv.sql}")
    print(f"  元数据: {conv.metadata}")
    
    # 转换为字典
    conv_dict = conv.to_dict()
    print(f"\n✓ 转换为字典格式")
    
    # 从字典创建
    conv_restored = Conversation.from_dict(conv_dict)
    print(f"✓ 从字典恢复对话对象")
    
    assert conv_restored.query == conv.query, "恢复的问题应该相同"
    assert conv_restored.sql == conv.sql, "恢复的SQL应该相同"
    
    print("\n" + "=" * 50)
    print("✓ 数据模型测试通过！")
    print("=" * 50)


if __name__ == "__main__":
    try:
        test_basic_context_operations()
        test_multiple_users()
        test_window_size()
        test_conversation_model()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！上下文管理功能正常工作！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
