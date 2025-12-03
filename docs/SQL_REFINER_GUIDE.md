
# SQL Refiner 功能指南

## 📋 概述

SQL Refiner 是一个实验性的自动SQL纠错模块，基于LLM反馈循环机制，能够自动检测和修复SQL执行过程中出现的错误。

## 🎯 功能特性

### 核心能力
1. **自动错误检测** - 捕获SQL执行时的各种错误
2. **智能错误分析** - 基于错误日志和Schema分析根因
3. **迭代式修复** - 通过多次尝试逐步修正SQL
4. **上下文感知** - 保留Schema和用户问题上下文
5. **错误历史学习** - 避免重复相同的错误

### 支持的错误类型
- ✅ 列名错误（如拼写错误、大小写问题）
- ✅ 表名不存在
- ✅ 语法错误（方言特定语法）
- ✅ 数据类型不匹配
- ✅ JOIN条件错误
- ✅ 聚合函数使用错误

## 🚀 快速开始

### 配置参数
在 `text2data` 工具中启用以下参数：
- `enable_refiner`: true (启用SQL Refiner)
- `max_refine_iterations`: 3 (最大修复尝试次数)

### 使用示例
```python
{
    "dataset_id": "your_dataset_id",
    "llm": "your_llm_model",
    "content": "查询所有用户的订单数量",
    "dialect": "mysql",
    "enable_refiner": true,
    "max_refine_iterations": 3
}
```

## 🔧 工作原理

### 流程
1. 用户问题 → 生成初始SQL
2. 执行SQL查询 → 如果失败且启用Refiner
3. SQL Refiner循环：
   - 捕获错误信息
   - 构建修复Prompt
   - LLM生成新SQL
   - 验证新SQL
   - 迭代（最多N次）
4. 返回修复后的SQL或错误报告

## 📊 使用案例

### 案例：列名拼写错误
**原始问题**: 查询所有用户的姓名和邮箱
**错误SQL**: `SELECT name, email FROM users`
**错误信息**: Unknown column 'name' in 'field list'
**修复后**: `SELECT username, email FROM users`
**结果**: ✅ 第1次迭代成功

## ⚙️ 配置说明

### enable_refiner
- 类型: boolean
- 默认: false
- 说明: 是否启用SQL自动修复

### max_refine_iterations
- 类型: number
- 范围: 1-5
- 默认: 3
- 说明: 最大修复尝试次数

## 🎯 最佳实践

### 何时启用Refiner
✅ 推荐: Schema复杂、多表JOIN、用户问题不精确
❌ 不建议: 简单查询、性能要求高、生产环境

### 优化建议
- 提供详细的Schema信息
- 在示例知识库中添加常见查询模式
- 设置合理的迭代次数（推荐3次）

## 📈 监控与调试

### 日志示例
```
[INFO] SQL执行失败，启动SQL Refiner进行自动修复...
[INFO] SQL修复迭代 1/3
[WARNING] 第1次尝试失败: Unknown column 'name'
[INFO] SQL修复成功！迭代次数: 2
```

## ❓ 常见问题

**Q: Refiner会增加多少延迟？**
A: 每次迭代约2-3秒，总计约5-10秒

**Q: 消耗多少Token？**
A: 每次迭代约1700-3000 tokens

**Q: 修复失败怎么办？**
A: 系统会返回详细错误报告，建议检查Schema完整性或手动修复

## 🔒 安全性

- 修复后的SQL仍通过安全检查
- 仅修复SELECT查询
- 保留数据库权限控制

## 📚 相关文档
- [Text2Data 工具文档](../README.md)
- [数据库配置指南](./DATABASE_SUPPORT_UPDATE.md)
- [测试指南](./TESTING_GUIDE.md)