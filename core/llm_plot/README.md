# LLM Plot 核心模块

这是 LLM Plot 工具的核心模块，采用模块化设计，便于维护和扩展。

## 📁 目录结构

```
core/llm_plot/
├── __init__.py           # 模块初始化和导出
├── README.md             # 本文档
├── models.py             # 数据模型定义
├── config.py             # 配置和模板管理
├── validator.py          # 参数验证
├── data_processor.py     # 数据处理和转换
├── llm_analyzer.py       # LLM 分析和推荐
└── chart_generator.py    # 图表生成
```

## 📦 模块说明

### 1. models.py - 数据模型
定义核心数据结构：
- `ChartRecommendation`: 图表推荐模型，包含图表类型、字段、标题等信息

### 2. config.py - 配置管理
提供图表配置和模板：
- `ChartConfig.BASE_CONFIG`: 基础配置模板
- `ChartConfig.LINE_CHART_TEMPLATE`: 折线图模板
- `ChartConfig.HISTOGRAM_CHART_TEMPLATE`: 直方图模板
- `ChartConfig.PIE_CHART_TEMPLATE`: 饼图模板
- `ChartConfig.get_chart_template()`: 获取指定类型的模板
- `ChartConfig.create_chart_config()`: 创建完整的图表配置

#### 图表模板特性

**折线图模板**
- 平滑曲线渲染
- 可自定义线宽
- 支持图例和工具提示
- 适用于时间序列和趋势分析

**直方图模板**
- 自适应区间数量
- 淡雅背景色设计
- 展示数据分布情况
- 适用于频数统计

**饼图模板**
- 环形图设计 (innerRadius: 0.5)
- 右侧图例布局
- 内部标签显示
- 统计信息展示
- 适用于占比和结构分析

### 3. validator.py - 参数验证
提供参数验证功能：
- `validate_parameters()`: 验证必需参数
- `validate_data_format()`: 验证数据格式
- `validate_chart_type()`: 验证图表类型
- `validate_field_exists()`: 验证字段存在性

### 4. data_processor.py - 数据处理
处理和转换数据：
- `transform_data_for_chart()`: 转换数据为图表格式
- `clean_data()`: 数据清洗
- `get_data_summary()`: 获取数据摘要

支持的转换：
- **折线图**: `[{"time": "...", "value": ...}, ...]`
- **直方图**: `[value1, value2, ...]`
- **饼图**: `[{"category": "...", "value": ...}, ...]`

### 5. llm_analyzer.py - LLM 分析
使用 LLM 分析数据并推荐图表：
- `analyze()`: 分析用户问题和 SQL 查询
- `create_recommendation()`: 创建图表推荐
- 智能推荐最适合的图表类型
- 提供默认推荐配置

### 6. chart_generator.py - 图表生成
生成和配置图表：
- `generate_chart_config()`: 生成图表配置
- `generate_chart_url()`: 调用 AntV API 生成图表
- `generate()`: 完整的图表生成流程

## 🎨 使用示例

### 基础使用

```python
from core.llm_plot import (
    ParameterValidator,
    LLMAnalyzer,
    ChartGenerator,
)

# 1. 验证参数
ParameterValidator.validate_parameters(parameters)

# 2. LLM 分析
analyzer = LLMAnalyzer(session)
recommendation = analyzer.analyze(user_question, sql_query, llm_model)

# 3. 生成图表
generator = ChartGenerator()
chart_url = generator.generate(recommendation, data)
```

### 自定义配置

```python
from core.llm_plot import ChartConfig

# 创建自定义折线图配置
config = ChartConfig.create_chart_config(
    chart_type="line",
    data=chart_data,
    title="销售趋势",
    x_title="日期",
    y_title="销售额",
    style={"lineWidth": 5}
)
```

### 数据处理

```python
from core.llm_plot import DataProcessor

processor = DataProcessor()

# 转换数据
chart_data = processor.transform_data_for_chart(
    chart_type="pie",
    data=raw_data,
    x_field="category",
    y_field="value"
)

# 获取数据摘要
summary = processor.get_data_summary(data)
print(f"记录数: {summary['record_count']}")
print(f"字段: {summary['fields']}")
```

## 🎯 设计优势

1. **模块化设计**: 每个模块职责单一，易于维护和测试
2. **可扩展性**: 便于添加新的图表类型和功能
3. **可复用性**: 核心功能可在其他项目中复用
4. **美观模板**: 预构建的专业图表模板
5. **类型安全**: 使用 Pydantic 模型进行类型验证
6. **错误处理**: 完善的异常处理和日志记录

## 🔧 配置说明

### 颜色调色板
```python
palette = [
    "#5B8FF9",  # 蓝色
    "#61DDAA",  # 绿色
    "#F6BD16",  # 黄色
    "#7262fd",  # 紫色
    "#78D3F8",  # 青色
    "#9661BC",  # 深紫色
    "#F6903D",  # 橙色
    "#008685",  # 青绿色
    "#F08BB4",  # 粉色
]
```

### AntV API 配置
- **URL**: `https://antv-studio.alipay.com/api/gpt-vis`
- **超时**: 30 秒
- **主题**: academy
- **默认尺寸**: 800x500 (折线图/直方图), 600x400 (饼图)

## 📝 版本信息

- **版本**: 1.0.0
- **Python**: >= 3.8
- **依赖**: pydantic, requests, dify_plugin

## 🤝 贡献指南

添加新功能时，请遵循以下原则：
1. 保持模块职责单一
2. 添加完整的文档字符串
3. 编写单元测试
4. 保持代码风格一致
5. 更新此 README 文档