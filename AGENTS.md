# PPTX Agent 项目规范

## 技术栈
- Python 3.10+
- FastAPI + Uvicorn
- python-pptx (PPTX操作)
- mysql-connector-python (MySQL)
- openai (LLM)
- markitdown (文档转换)
- mermaid-cli (图表渲染)

## 代码风格
- 使用英文命名，中文仅用于用户界面和文档
- 类型注解 encouraged
- 每个模块有独立的 logger
- 异常必须捕获并记录

## 目录约定
- `skills/` - 外部工具封装，每个skill有SKILL.md
- `core/` - 业务逻辑
- `database/` - DAO层
- `models/` - Pydantic schemas
- `logs/` - 每job一个子目录，保存检查点

## 数据库
- MySQL 127.0.0.1:3306, root/空密码
- 数据库名: pptx_agent
- 表: templates, template_pages, generation_jobs

## 环境变量
- LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
- MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

## 开发注意事项
- 先运行 `init_db()` 确保表存在
- 模板分析是独立脚本，不依赖web服务
- Agent每步有检查点文件，可独立调试
