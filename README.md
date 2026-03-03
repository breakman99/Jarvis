# Jarvis
personal intelligent assistant
一个简单的本地可运行的 Python Agent 框架。

## 功能特性

- 🤖 基础的 Agent 实现
- 💭 思考能力
- 🎯 动作执行
- 🧠 记忆管理
- 📝 日志记录

## 项目结构

```
.
├── agent.py          # Agent 主程序
├── requirements.txt  # 项目依赖
├── .env.example     # 环境变量示例
├── .gitignore       # Git 忽略文件
└── README.md        # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key 等配置
```

### 3. 运行 Agent

```bash
python agent.py
```

## 使用示例

```python
from agent import SimpleAgent

# 创建 Agent
agent = SimpleAgent(name="MyAgent")

# Agent 思考
thought = agent.think("完成某个任务")
print(thought)

# Agent 执行动作
result = agent.act("greet")
print(result)

# 查看记忆
memory = agent.get_memory()
print(f"记忆数量: {len(memory)}")
```

## 扩展开发

这个框架提供了基础结构，你可以在此基础上扩展：

- 添加 LLM API 集成（OpenAI、Anthropic 等）
- 实现工具调用功能
- 添加向量数据库支持
- 实现更复杂的记忆系统
- 添加多 Agent 协作能力

## 依赖说明

- `python-dotenv`: 环境变量管理
- `requests`: HTTP 请求
- `colorlog`: 彩色日志输出

## 许可证

MIT License
