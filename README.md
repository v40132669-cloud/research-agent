# 🔍 自动化研报 Agent

基于 **LangGraph** 的多智能体调研系统，实现从调研规划、信息检索、结构化分析到投行风格报告生成的全流程自动化。支持多模型切换、自反思重试机制和实时流式输出。

## ✨ 功能特性

- **智能规划**：自动拆解调研主题为 3-5 个专业检索维度
- **并行搜索**：集成 Tavily/SerpAPI，支持高级搜索深度和 PDF 内容提取
- **Map-Reduce 分析**：先去噪提取单篇材料，再汇总交叉验证
- **自反思重试**：Reviewer 发现信息缺口自动回退重规划（最多 2 轮）
- **多模型支持**：OpenAI、Anthropic Claude、阿里云 Qwen、讯飞星火
- **状态持久化**：SQLite 断点续跑 + LangSmith 链路观测
- **双端交付**：命令行工具 + Web 可视化界面（支持实时流式输出）

## 🏗️ 架构设计

```
START → Planner → Researcher → Analyst → Reviewer → [Planner ↻ / Writer] → END
```

| 节点 | 职责 | 核心能力 |
|------|------|----------|
| **Planner** | 调研规划 | 生成检索维度与查询词 |
| **Researcher** | 信息检索 | 并行调用搜索 API，支持 PDF 解析 |
| **Analyst** | 结构化分析 | Map-Reduce 事实提取与交叉验证 |
| **Reviewer** | 质量审核 | 自反思决策路由，最多 2 轮重试 |
| **Writer** | 报告撰写 | 投行风格结构化 Markdown 输出 |

## 🛠️ 技术栈

| 分类 | 技术 | 版本要求 |
|------|------|----------|
| 多智能体框架 | LangGraph | >= 0.2.60 |
| 状态持久化 | LangGraph SQLite Checkpointer | >= 2.0.0 |
| LLM 集成 | LangChain-OpenAI / LangChain-Anthropic | - |
| 搜索服务 | Tavily Search / SerpAPI | - |
| PDF 解析 | PyMuPDF | >= 1.24.14 |
| Web 服务 | FastAPI + Uvicorn | - |
| 模板引擎 | Jinja2 | >= 3.1.2 |

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- 所需 API Key（见配置说明）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并填入必要的 API Key：

```bash
# 模型配置（四选一）
MODEL_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# 搜索服务（二选一）
TAVILY_API_KEY=your_key_here
# 或
SERPAPI_API_KEY=your_key_here
```

### 运行方式

**命令行模式**：
```bash
python main.py "Tesla 2024 财报分析"
```

**Web 服务模式**：
```bash
python web_app.py
# 访问 http://localhost:7000
```

**一键启动脚本**：
```bash
# Windows
start.bat

# macOS/Linux
./start.sh
```

## 🔧 配置说明

### 模型供应商

| Provider | 环境变量 | 说明 |
|----------|----------|------|
| OpenAI | `MODEL_PROVIDER=openai` | 默认，支持自定义 base_url（如腾讯混元） |
| Anthropic | `MODEL_PROVIDER=anthropic` | Claude 3.5 Sonnet |
| Qwen | `MODEL_PROVIDER=qwen` | 阿里云百炼，OpenAI 兼容接口 |
| Xunfei | `MODEL_PROVIDER=xunfei` | 讯飞星火，WebSocket 原生协议 |

### 搜索服务

| Provider | 环境变量 |
|----------|----------|
| Tavily | `SEARCH_PROVIDER=tavily`（默认） |
| SerpAPI | `SEARCH_PROVIDER=serpapi` |

### 环境变量完整列表

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MODEL_PROVIDER` | LLM 供应商 | openai |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_MODEL` | OpenAI 模型 | gpt-4o |
| `OPENAI_BASE_URL` | OpenAI 自定义端点 | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `ANTHROPIC_MODEL` | Anthropic 模型 | claude-3-5-sonnet-20241022 |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key | - |
| `QWEN_MODEL` | Qwen 模型 | qwen3-max |
| `XUNFEI_API_KEY` | 讯飞 API Key（格式：key:secret） | - |
| `XUNFEI_APP_ID` | 讯飞 App ID | - |
| `TAVILY_API_KEY` | Tavily API Key | - |
| `SERPAPI_API_KEY` | SerpAPI API Key | - |
| `TAVILY_MAX_RESULTS` | 搜索最大结果数 | 8 |
| `TAVILY_TOP_K` | 每查询截取数量 | 5 |
| `MODEL_TEMPERATURE` | LLM 温度参数 | 0.2 |
| `LANGGRAPH_DEBUG` | 调试模式 | false |
| `LANGGRAPH_CHECKPOINT_DB` | SQLite 数据库路径 | agent_state.db |
| `LANGSMITH_TRACING` | LangSmith 追踪 | false |
| `LANGSMITH_API_KEY` | LangSmith API Key | - |
| `PORT` | Web 服务端口 | 7000 |

## 📊 使用示例

```bash
# 调研特斯拉财报
python main.py "Tesla 2024 财报分析"

# 调研人工智能行业趋势
python main.py "AI 大模型 2024 发展趋势"

# 调研新能源汽车市场
python main.py "新能源汽车 2024 市场份额"

# 调研特定公司
python main.py "字节跳动 业务布局 2024"
```

## 📁 项目结构

```
├── main.py              # 命令行入口
├── web_app.py           # Web 服务入口（FastAPI）
├── graph.py             # LangGraph 工作流定义
├── nodes.py             # 5个智能体节点实现
├── state.py             # AgentState 状态数据结构
├── tools.py             # 搜索工具封装（Tavily/SerpAPI）
├── debug_loader.py      # 调试加载器
├── test_template.py     # 模板测试
├── requirements.txt     # 依赖清单
├── .env.example         # 环境变量模板
├── .gitignore           # Git 忽略配置
├── Dockerfile           # Docker 配置
├── start.bat            # Windows 启动脚本
├── start.ps1            # PowerShell 启动脚本
├── start.sh             # Linux/macOS 启动脚本
├── static/              # 静态资源（CSS）
└── templates/           # Web 页面模板
```

## 📝 输出报告结构

生成的投行风格研报包含以下结构化内容：

1. **背景** - 行业概况与调研背景
2. **核心竞争力** - 企业/行业核心优势分析
3. **SWOT 分析** - 优势、劣势、机会、威胁
4. **风险提示** - 潜在风险因素与不确定性
5. **结论** - 综合判断与投资建议
6. **参考来源** - 所有引用链接与数据来源

## 🔄 工作流程图

```mermaid
flowchart TD
    A[START] --> B[Planner<br/>规划调研维度]
    B --> C[Researcher<br/>并行搜索]
    C --> D[Analyst<br/>Map-Reduce分析]
    D --> E[Reviewer<br/>质量审核]
    E -->|审核通过| F[Writer<br/>生成报告]
    E -->|需要补充| B
    F --> G[END]
```

## 🌐 API 接口

### 启动调研（同步）
```
POST /api/research
Content-Type: application/json

{
    "topic": "Tesla 2024 财报分析"
}
```

### 启动调研（流式）
```
POST /api/research/stream
Content-Type: application/json

{
    "topic": "Tesla 2024 财报分析"
}
```

**流式响应格式**：
```json
{
    "type": "plan|research|analysis|review|report|complete",
    "data": { ... }
}
```

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -t research-agent .

# 运行容器
docker run -p 7000:7000 --env-file .env research-agent
```

## 🔍 可观测性

### LangSmith 追踪

配置以下环境变量启用 LangSmith 链路观测：

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=research-agent
```

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- GitHub Issues: [https://github.com/v40132669-cloud/research-agent/issues](https://github.com/v40132669-cloud/research-agent/issues)