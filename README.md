# Business Intelligence System

业务情报系统 - 智能情报采集与管理平台

## 功能特性

- **情报源管理** - 配置和管理多个情报来源，支持网站、API、RSS等类型
- **代理池管理** - 代理IP池配置，支持质量评分和自动禁用
- **UA池管理** - User-Agent字符串池，支持随机选取
- **任务调度** - 自动化采集任务，支持暂停、恢复、取消操作
- **情报详情** - 结构化情报数据存储与搜索

## 技术栈

- Python 3.10+
- FastAPI - Web框架
- SQLAlchemy - ORM
- SQLite/PostgreSQL - 数据库

## 快速开始

### 安装依赖

```bash
pip install -e .
```

### 启动服务

```bash
python -m uvicorn bis.main:app --host 0.0.0.0 --port 8000
```

### 访问应用

- 首页: http://localhost:8000/
- API文档: http://localhost:8000/docs

## 项目结构

```
src/bis/
├── api/              # API路由层
├── core/             # 核心配置
├── models/           # 数据模型
├── repositories/     # 数据访问层
├── services/         # 业务逻辑层
├── templates/        # 前端模板
└── main.py           # 应用入口
```

## API端点

| 模块 | 端点前缀 |
|------|----------|
| 情报源 | /api/v1/sources |
| 代理池 | /api/v1/proxies |
| UA池 | /api/v1/user-agents |
| 任务 | /api/v1/tasks |
| 情报 | /api/v1/intelligence |

## 配置

配置文件: `config.yaml`

主要配置项:
- `database.url` - 数据库连接地址
- `app.host` - 服务监听地址
- `app.port` - 服务监听端口

## License

MIT
