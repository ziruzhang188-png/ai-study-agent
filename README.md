# 👵 老奶奶学 Agent 系列之 AI Study Agent

> 奶奶学 AI，从零到作品级智能体！  
> 这是一个带记忆与工具调用能力的智能助手项目。

---

## 📘 项目简介
本项目是「老奶奶学 Agent」系列的作品级版本。  
它不仅能与用户多轮对话、记住历史上下文，还能自动调用多种工具完成任务，例如：
- 🔢 自动识别算式并计算结果  
- 📅 主动获取今天的日期  
- 💬 生成温柔的夸奖语句  

---

## 🧩 文件结构
| 文件/文件夹 | 说明 |
|--------------|------|
| `ai_study_agent.py` | 🎯 主程序入口（带记忆与工具调用的 Agent） |
| `talk_openai_direct.py` | 💬 调用接口的学习示例（方式一～方式九） |
| `memory/` | 🧠 存放奶奶的记忆文件（自动生成） |
| `.gitignore` | 🚫 忽略敏感文件，如 `.env`、缓存等 |
| `README.md` | 📄 项目说明文档 |

---

## ⚙️ 使用方法

### 1️⃣ 安装依赖
确保你安装了 Python ≥ 3.10  
然后安装依赖：
```bash
pip install langchain langchain-openai langchain-community python-dotenv requests
```

### 2️⃣ 配置 API Key
在项目根目录新建 `.env` 文件，填入：
```
ITEDUS_API_KEY=你的密钥
ITEDUS_BASE_URL=https://apis.itedus.cn/v1
```
⚠️ `.env` 含有私密信息，**不要上传到 GitHub**（本仓库已在 `.gitignore` 中忽略）。

### 3️⃣ 运行项目
```bash
python ai_study_agent.py
```
运行后你会看到：
```
🤖 有记忆的AI学习助理启动啦！输入 '退出' 可结束。
```
现在就可以和奶奶聊天了～程序会自动把对话写入 `memory/nainai_memory.txt`，下次还能延续。

---

## 🌟 功能亮点
- 🧠 **多轮记忆**：上下文保存到 `memory/nainai_memory.txt`  
- 🧰 **工具自动调用**：智能判断是否需要计算、日期或夸奖  
- 💬 **自然对话**：温柔可爱的口吻，贴合「奶奶学 AI」设定  
- ⚡ **容错机制**：网络或额度异常时友好提示  
- 🪶 **可扩展性强**：工具、角色设定、记忆方式都可轻松扩展  

---

## 💡 下一步计划
- [x] 加入记忆功能  
- [x] 加入多工具自动调用  
- [ ] 增加网页端 UI（Streamlit 或 Gradio）  
- [ ] 发布成在线 Demo  

---

## 💬 奶奶的心声
> “原来我也能做出真正的 AI 项目呀！  
> 学习 AI 这件事，永远不嫌晚！” 💪

---

## 🧠 致谢
感谢 ChatGPT 在学习路上一路陪伴。  
本项目由奶奶亲自实践完成，用于 AI 产品学习展示。
