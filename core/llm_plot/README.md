# LLM 智能绘图模块

基于 LLM 的智能图表生成功能，提供高可维护的端到端图表生成解决方案。

## 功能特性

- 🤖 **智能分析**: 基于 LLM 自动分析用户问题和数据，选择最合适的图表类型
- 📊 **多图表支持**: 支持柱状图、折线图、饼图、散点图、直方图
- 🔧 **高可维护**: 模块化设计，清晰的接口分离
- 📝 **统一规范**: 标准化的 JSON 配置格式
- 🛡️ **降级方案**: 当图表生成失败时，提供表格等降级展示
- ✅ **配置验证**: 完善的配置验证和错误处理

## 架构设计

### 四层架构

1. **配置层** (`chart_schema.py`): 定义统一的 JSON 配置规范
2. **绘图层** (`chart_generator.py`): Matplotlib 图表生成引擎
3. **智能层** (`chart_prompts.py`): LLM Prompt 设计和管理
4. **控制层** (`chart_controller.py`): 端到端的流程控制

### 模块关系

```
用户问题 + 数据
        ↓
    控制层 (Controller)
        ↓
    智能层 (Prompts) → LLM
        ↓
    配置层 (Schema) - 验证
        ↓
    绘图层 (Generator) → 图表文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install matplotlib pydantic
```

### 2. 基本使用

```python
from core.llm_plot import initialize_chart_service, generate_smart_chart

# 初始化服务（需要提供 LLM 客户端）
initialize_chart_service(llm_client=your_llm_client)

# 智能生成图表
user_question = "显示最近三个月的销售额变化"
query_data = [
    {"month": "2025-01", "sales": 120},
    {"month": "2025-02", "sales": 135}, 
    {"month": "2025-03", "sales": 98}
]

result = generate_smart_chart(user_question, query_data)

if result["success"]:
    print(f"图表已生成: {result['chart_path']}")
else:
    print(f"生成失败: {result['error']}")
```

### 3. 直接使用配置

```python
from core.llm_plot import generate_chart

# 使用预定义配置
config = {
    "chart_type": "bar",
    "title": "销售额统计",
    "x_axis": {
        "label": "月份",
        "data": ["1月", "2月", "3月"]
    },
    "y_axis": {
        "label": "销售额 (万元)",
        "data": [120, 135, 98]
    }
}

chart_path = generate_chart(config)
print(f"图表已生成: {chart_path}")
```

## 配置规范

### 支持的图表类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `bar` | 柱状图 | 比较不同类别的数值 |
| `line` | 折线图 | 显示趋势变化 |
| `pie` | 饼图 | 显示比例分布 |
| `scatter` | 散点图 | 显示相关性 |
| `histogram` | 直方图 | 显示分布情况 |

### JSON 配置格式

#### 柱状图配置
```json
{
  "chart_type": "bar",
  "title": "图表标题",
  "x_axis": {
    "label": "X轴标签",
    "data": ["类别1", "类别2", "类别3"]
  },
  "y_axis": {
    "label": "Y轴标签", 
    "data": [10, 20, 15]
  }
}
```

#### 折线图配置
```json
{
  "chart_type": "line",
  "title": "图表标题",
  "x_axis": {
    "label": "X轴标签",
    "data": ["时间1", "时间2", "时间3"]
  },
  "line_series": [
    {
      "label": "数据系列1",
      "data": [10, 15, 12]
    },
    {
      "label": "数据系列2", 
      "data": [8, 12, 14]
    }
  ]
}
```

#### 饼图配置
```json
{
  "chart_type": "pie",
  "title": "图表标题",
  "pie_data": {
    "labels": ["标签1", "标签2", "标签3"],
    "values": [30, 40, 30]
  }
}
```

### 样式配置（可选）
```json
{
  "style": {
    "figure_size": [10, 6],
    "dpi": 100,
    "grid": true,
    "colors": ["#1f77b4", "#ff7f0e", "#2ca02c"]
  }
}
```

## API 参考

### 核心类

#### `ChartGenerator`
图表生成器，负责根据配置生成 Matplotlib 图表。

```python
generator = ChartGenerator(output_dir="output/charts")
chart_path = generator.generate_chart(config)
```

#### `LLMChartController`
LLM 图表控制器，提供端到端的图表生成流程。

```python
controller = LLMChartController(llm_client=client)
result = controller.generate_chart_from_data(question, data)
```

### 工具函数

#### `validate_chart_config(config: Dict) -> ChartConfig`
验证图表配置的有效性。

#### `get_chart_template(chart_type: str) -> Dict`
获取指定图表类型的配置模板。

#### `create_chart_prompt(question: str, data: Any) -> str`
创建 LLM Prompt。

### 服务函数

#### `initialize_chart_service(llm_client, output_dir)`
初始化全局图表服务。

#### `generate_smart_chart(question: str, data: Any) -> Dict`
智能生成图表的便捷函数。

## 高级用法

### 自定义 LLM 客户端

LLM 客户端需要实现 `chat` 方法：

```python
class CustomLLMClient:
    def chat(self, prompt: str) -> str:
        # 调用你的 LLM API
        response = your_llm_api.call(prompt)
        return response

# 使用自定义客户端
initialize_chart_service(llm_client=CustomLLMClient())
```

### 自定义样式

```python
config = {
    "chart_type": "bar",
    "title": "自定义样式图表",
    "x_axis": {"label": "类别", "data": ["A", "B"]},
    "y_axis": {"label": "数值", "data": [10, 20]},
    "style": {
        "figure_size": [12, 8],
        "dpi": 150,
        "colors": ["#FF6B6B", "#4ECDC4"]
    }
}
```

### 错误处理和降级

```python
result = generate_smart_chart(question, data)

if not result["success"]:
    print(f"图表生成失败: {result['error']}")
    
    # 使用降级数据
    if result.get("fallback_data"):
        fallback = result["fallback_data"]
        if fallback["type"] == "table":
            # 显示表格
            print("表格数据:")
            print(f"表头: {fallback['headers']}")
            for row in fallback["rows"]:
                print(f"数据: {row}")
```

## 运行示例

### 运行完整示例
```bash
cd core/llm_plot
python examples.py
```

### 运行测试
```bash
cd core/llm_plot
python test_llm_plot.py
```

## 文件结构

```
core/llm_plot/
├── __init__.py              # 模块初始化
├── chart_schema.py          # 配置规范定义
├── chart_generator.py       # Matplotlib 绘图引擎
├── chart_prompts.py         # LLM Prompt 模板
├── chart_controller.py      # 端到端控制逻辑
├── examples.py              # 使用示例
├── test_llm_plot.py         # 单元测试
└── README.md                # 文档说明
```

## 扩展指南

### 添加新图表类型

1. 在 `chart_schema.py` 中添加新类型到 `SUPPORTED_CHART_TYPES`
2. 在 `chart_generator.py` 中实现生成函数
3. 在主分发函数中添加路由
4. 更新配置规范和示例

### 自定义 Prompt

继承 `ChartPromptTemplate` 类：

```python
class CustomPromptTemplate(ChartPromptTemplate):
    def generate_prompt(self, question, data, context=None):
        # 自定义 Prompt 逻辑
        return custom_prompt
```

## 注意事项

1. **字体支持**: 默认配置支持中文字体，如遇显示问题请检查系统字体
2. **输出目录**: 确保指定的输出目录有写入权限
3. **内存管理**: 图表生成后会自动关闭 matplotlib 图形，避免内存泄漏
4. **LLM 响应**: LLM 响应需要是有效的 JSON 格式，建议在 Prompt 中强调

## 许可证

本模块遵循项目的整体许可证。
