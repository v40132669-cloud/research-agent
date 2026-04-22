# 自动化研报 Agent

基于 LangGraph 的多智能体调研系统，支持多步规划、并行搜索、Map-Reduce 分析、自反思重试，以及投行风格 Markdown 报告输出。

## 架构

- `Planner`：生成 3-5 个调研维度与专业检索词，支持根据 Reviewer 反馈重新规划。
- `Researcher`：并行调用 Tavily，固定使用 `search_depth="advanced"` 与 `include_raw_content=True`，并按相关性截取每个 query 的前 5 条结果。
- `Analyst`：采用 Map-Reduce，对单篇材料先做去噪提取，再汇总为统一分析结构。
- `Reviewer`：对比 Planner 维度与 Analyst 结果，发现缺口后回退给 Planner 重规划，最多 2 轮。
- `Writer`：输出投行风格的结构化 Markdown 报告。

## 运行

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入：

- `TAVILY_API_KEY`
- `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`
- 可选 `LANGSMITH_API_KEY`

3. 命令行运行

```bash
python main.py "Tesla"
```

4. Web 运行

```bash
python web_app.py
```

默认访问地址：`http://localhost:8080`

## 持久化与观测

- 默认优先使用 SQLite Checkpointer，数据库位置由 `LANGGRAPH_CHECKPOINT_DB` 控制。
- 若本地未安装 SQLite checkpointer 依赖，则自动回退到内存版 checkpointer。
- 若配置 `LANGSMITH_TRACING=true` 与相关 Key，可接入 LangSmith 观测节点耗时与链路。

## 多模型支持

- `MODEL_PROVIDER=openai`：默认 OpenAI
- `MODEL_PROVIDER=anthropic`：Claude
- `MODEL_PROVIDER=qwen`：阿里云百炼 Qwen，走 OpenAI 兼容接口
- `MODEL_PROVIDER=xunfei`：讯飞星火，走原生 WebSocket
