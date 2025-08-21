# LLM 智能绘图工具 - Dify 集成指南

## 概述

LLM 智能绘图工具是一个强大的 Dify 自定义工具，能够根据用户的自然语言问题和数据自动生成合适的图表。工具使用 LLM 进行智能分析，选择最佳的图表类型并生成美观的可视化图表。

## 功能特性

- 🤖 **智能分析**: 使用 LLM 分析用户问题，自动选择最合适的图表类型
- 📊 **多图表支持**: 支持柱状图、折线图、饼图、散点图、直方图
- 🎨 **美观设计**: 现代化的图表样式，支持中文显示
- 🛡️ **错误处理**: 完善的错误处理和降级方案
- 🔗 **Dify 集成**: 完全兼容 Dify 工作流

## 快速开始

### 1. 在 Dify 中添加自定义工具

1. 进入 Dify 工作空间
2. 选择"工具" → "自定义工具"
3. 点击"创建自定义工具"
4. 上传 `tools/llm_plot.yaml` 配置文件

### 2. 配置环境变量

在 `.env` 文件中添加以下配置：

```env
# LLM 配置
LLM_PROVIDER=dify  # 或 openai
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_base_url
LLM_MODEL=gpt-3.5-turbo
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7

# Dify 配置（如果使用 Dify LLM）
DIFY_API_KEY=your_dify_api_key
DIFY_BASE_URL=https://api.dify.ai/v1
```

### 3. 在工作流中使用

在 Dify 工作流中添加 LLM 绘图工具节点：

#### 输入参数:
- **user_question**: 用户问题（如："显示销售趋势"）
- **data**: 数据（JSON 字符串格式）
- **context**: 额外上下文（可选）

#### 输出结果:
- **success**: 是否成功生成图表
- **chart_path**: 图表文件路径
- **chart_url**: 图表访问链接
- **chart_type**: 图表类型
- **message**: 结果消息

## 使用示例

### 示例 1: 销售数据柱状图

```json
{
  "user_question": "显示各季度销售额对比",
  "data": "[{\"quarter\":\"Q1\",\"sales\":150},{\"quarter\":\"Q2\",\"sales\":180},{\"quarter\":\"Q3\",\"sales\":165},{\"quarter\":\"Q4\",\"sales\":200}]"
}
```

**预期输出**: 自动生成柱状图

### 示例 2: 销售趋势折线图

```json
{
  "user_question": "分析销售额的变化趋势",
  "data": "[{\"month\":\"1月\",\"sales\":120},{\"month\":\"2月\",\"sales\":135},{\"month\":\"3月\",\"sales\":98},{\"month\":\"4月\",\"sales\":156}]"
}
```

**预期输出**: 自动生成折线图

### 示例 3: 市场份额饼图

```json
{
  "user_question": "显示各公司的市场份额分布",
  "data": "[{\"company\":\"公司A\",\"share\":35.2},{\"company\":\"公司B\",\"share\":28.7},{\"company\":\"公司C\",\"share\":22.1},{\"company\":\"其他\",\"share\":14.0}]"
}
```

**预期输出**: 自动生成饼图

## 工作流集成模式

### 模式 1: 数据查询 + 图表生成

```
用户输入 → SQL查询工具 → LLM绘图工具 → 返回图表
```

1. 用户提问："显示最近三个月的销售情况"
2. SQL 工具查询数据
3. LLM 绘图工具生成图表
4. 返回图表链接给用户

### 模式 2: 直接数据可视化

```
数据输入 → LLM绘图工具 → 返回图表
```

1. 直接提供数据和可视化需求
2. LLM 绘图工具分析并生成图表
3. 返回结果

## 高级配置

### 自定义样式

可以在数据中包含样式配置：

```json
{
  "user_question": "生成自定义样式的销售图表",
  "data": "...",
  "context": "使用蓝色系配色方案，图表尺寸 14x8"
}
```

### 错误处理

当图表生成失败时，工具会：

1. 返回详细错误信息
2. 提供降级数据展示方案
3. 尝试使用默认配置生成简单图表

## 文件结构

```
tools/
├── llm_plot.py              # 工具主要实现
├── llm_plot.yaml            # Dify 工具配置
├── test_llm_plot.py         # 测试文件
└── README_llm_plot.md       # 本文档

core/llm_plot/
├── __init__.py              # 模块初始化
├── chart_schema.py          # 图表配置规范
├── chart_generator.py       # 图表生成器（已美化）
├── chart_prompts.py         # LLM Prompt 模板
├── chart_controller.py      # 控制器
├── examples.py              # 使用示例
└── README.md                # 核心模块文档
```

## 测试

运行测试验证功能：

```bash
cd tools
python test_llm_plot.py
```

## 故障排除

### 常见问题

1. **图表生成失败**
   - 检查 LLM API 配置
   - 验证数据格式是否正确
   - 查看错误日志

2. **中文显示异常**
   - 确保系统已安装中文字体
   - 检查 matplotlib 字体配置

3. **图表访问链接无效**
   - 确保静态文件服务配置正确
   - 检查文件路径权限

### 调试模式

设置环境变量启用调试：

```env
LOG_LEVEL=DEBUG
```

## 扩展开发

### 添加新图表类型

1. 在 `chart_schema.py` 中添加新类型
2. 在 `chart_generator.py` 中实现生成函数
3. 更新 YAML 配置文件

### 自定义 LLM 客户端

在 `config.py` 中实现自定义客户端：

```python
def get_custom_llm_client():
    class CustomClient:
        def chat(self, prompt):
            # 实现你的逻辑
            return response
    return CustomClient()
```

## 许可证

本工具遵循项目的整体许可证。
