把已有“记忆 + 工具调用”的 Agent 接成网页，带**聊天气泡**和**侧边栏设置**。


## 本地运行
```bash
# 1) 克隆你的仓库
# git clone https://github.com/<你的用户名>/<你的仓库>.git
# cd <你的仓库>


# 2) 安装依赖
pip install -r requirements.txt


# 3) 运行
streamlit run app.py
```
打开浏览器即可。侧边栏可以填 **API Key / Base URL / 模型名**，也可以改 **System Prompt**、开关**记忆**。


## 对接你的 Agent
打开 `app.py`，把 `AgentAdapter._call_agent` 中的“示例返回”换成你项目的真实调用，例如：
```python
reply_text, tool_calls = your_agent.invoke(messages) # 由你项目提供
return AgentOutput(text=reply_text, tool_calls=tool_calls or [], latency_ms=latency)
```


## 云端部署（任选其一）
### A. Streamlit Community Cloud（免服务器）
1. 仓库包含 `app.py` 与 `requirements.txt`。
2. 访问 https://share.streamlit.io ，连接 GitHub，选仓库，一键部署。
3. 在 Secrets 里设置 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`（可选）。


### B. Render / Railway（通用 PaaS）
- Build：`pip install -r requirements.txt`
- Run：`streamlit run app.py --server.port $PORT --server.address 0.0.0.0`


## 常见问题
- **我用第三方大模型网关？** → 在 Sidebar 或环境变量改 `Base URL`。
- **不想显示工具调用？** → Sidebar 关闭“显示工具调用记录”。
- **不想保留记忆？** → Sidebar 关闭“保留上下文记忆”。
- **要日志？** → 在 `adapter.chat` 前后加入你的 logger。


## 许可证
按你仓库 LICENSE；若无，可用 MIT。