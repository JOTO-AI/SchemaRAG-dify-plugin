# SchemaRAG Plugin 使用说明

这是一个用于构建数据库架构RAG的Dify插件，能够自动分析数据库结构并上传到Dify知识库。

## 功能特性

- 🔍 自动分析MySQL/PostgreSQL数据库结构
- 📊 生成数据字典文档
- ☁️ 自动上传到Dify知识库
- 🚀 提供封装好的text2sql工具，开箱即用

## 配置参数

### 必需配置

- **Dataset API Key**: Dify知识库API密钥
- **Database Type**: 数据库类型（MySQL/PostgreSQL）
- **Database Host**: 数据库主机地址
- **Database Port**: 数据库端口（默认3306）
- **Database User**: 数据库用户名
- **Database Password**: 数据库密码
- **Database Name**: 数据库名称
- **Dify Base URL**: Dify API基础URL（默认：<https://api.dify.ai/v1）>

## 使用方式

