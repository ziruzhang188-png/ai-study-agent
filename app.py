import os
os.environ["OPENAI_API_KEY"] = "sk-mE3e4kW3oIYfnC9F0fC3Af298bE34f5aB264235562A0Db3a"
os.environ["OPENAI_BASE_URL"] = "https://apis.itedus.cn/v1"
os.environ["OPENAI_MODEL"] = "gpt-4o"

import time
import json
import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import requests
import streamlit as st
from duckduckgo_search import DDGS


# ===================== 0) 小工具：联网搜索 =====================
def web_search(query: str, max_results: int = 5) -> str:
    """
    用 DuckDuckGo 搜索，返回合并后的精简文本，方便喂给大模型。
    """
    if not query.strip():
        return ""
    items = []
    try:
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                # r: {'title','href','body'}
                title = r.get("title", "").strip()
                href = r.get("href", "").strip()
                body = r.get("body", "").strip()
                items.append(f"{i+1}. {title}\nURL: {href}\n摘要: {body}")
    except Exception as e:
        items.append(f"（搜索失败：{e}）")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    joined = "\n\n".join(items) if items else "（没有搜索结果）"
    return f"【联网搜索·{ts}】\n查询：{query}\n\n{joined}"


# ===================== 1) 适配器：调用 itedus.cn =====================
@dataclass
class AgentOutput:
    text: str
    tool_calls: List[Dict[str, Any]]
    latency_ms: int


class AgentAdapter:
    """
    把对话历史 messages 发到 itedus.cn，并返回回复。
    支持可选的“先联网搜索，再让模型综合回答”。
    """

    def __init__(self, base_url: Optional[str], api_key: Optional[str], model: str, system_prompt: str):
        # 默认 itedus；可被侧边栏/环境变量覆盖
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://apis.itedus.cn/v1").rstrip("/")
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self.model = (model or os.getenv("OPENAI_MODEL") or "gpt-4o").strip()
        self.system_prompt = system_prompt

    def _call_agent(
        self,
        messages: List[Dict[str, str]],
        auto_search: bool = False,
        search_k: int = 5
    ) -> AgentOutput:
        """真正去请求 itedus.cn 的 /chat/completions"""
        start = time.time()

        # 1) 注入“当前本机时间”的 system 提示（方便回答日期/星期）
        now = datetime.datetime.now()
        weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
        time_hint = (
            f"当前本机本地时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，"
            f"星期{weekday_map[now.weekday()] if now.weekday() < 7 else '?'}。"
            "当用户询问日期、星期或‘今天几号’等时，请基于此时间直接回答。"
        )

        msg_list = messages[:]
        if not msg_list or msg_list[0].get("role") != "system":
            msg_list = [{"role": "system", "content": self.system_prompt or ""}] + msg_list
        # 把时间提示也并入
        msg_list = [{"role": "system", "content": time_hint}] + msg_list

        # 2) 如勾选“自动联网搜索”，先查资料再给模型
        if auto_search:
            # 取用户最新一句作为搜索词
            last_user = ""
            for m in reversed(msg_list):
                if m.get("role") == "user":
                    last_user = m.get("content", "")
                    break
            search_text = web_search(last_user, max_results=search_k)
            # 把搜索结果作为 system 信息注入，要求“基于这些结果回答，并标注可能的不确定性”
            search_system = (
                "以下是联网搜索到的资料（可能包含噪声）。"
                "请先阅读，再结合用户问题给出**可信且简明**的答案；"
                "如资料不足或相互矛盾，请如实说明不确定性：\n\n" + search_text
            )
            msg_list = [{"role": "system", "content": search_system}] + msg_list

        # 3) 调 itedus.cn
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": msg_list,
        }

        reply_text = ""
        tool_calls: List[Dict[str, Any]] = []
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            result = resp.json() if resp.content else {}
            tool_calls.append(result)
            if resp.status_code != 200:
                err_msg = result.get("error", {}).get("message", f"HTTP {resp.status_code}")
                reply_text = f"❌ 接口返回错误：{err_msg}"
            else:
                reply_text = result["choices"][0]["message"]["content"]
        except Exception as e:
            reply_text = f"❌ 请求失败：{e}"

        latency = int((time.time() - start) * 1000)
        return AgentOutput(text=reply_text, tool_calls=tool_calls, latency_ms=latency)

    def chat(self, history: List[Dict[str, str]], user_text: str, auto_search: bool, search_k: int) -> AgentOutput:
        messages = history + [{"role": "user", "content": user_text}]
        return self._call_agent(messages, auto_search=auto_search, search_k=search_k)


# ===================== 2) Streamlit UI（聊天气泡 + 侧边栏） =====================
st.set_page_config(page_title="Agent7 Web", page_icon="🤖", layout="centered")

# --- Sidebar: 设置 ---
st.sidebar.title("⚙️ 设置")
api_key = st.sidebar.text_input("API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
base_url = st.sidebar.text_input("Base URL", value=os.getenv("OPENAI_BASE_URL", "https://apis.itedus.cn/v1"))
model = st.sidebar.text_input("模型名", value=os.getenv("OPENAI_MODEL", "gpt-4o"))

with st.sidebar.expander("对话与显示"):
    default_system = "你是中文助理，会在需要时使用工具并保留对话记忆，回答简洁友好。"
    system_prompt = st.text_area("System Prompt（可选）", value=default_system, height=100)
    show_tools = st.checkbox("显示工具调用记录", value=True)
    show_latency = st.checkbox("显示响应耗时", value=True)
    keep_memory = st.checkbox("保留上下文记忆（关掉则每次当新对话）", value=True)

with st.sidebar.expander("联网搜索（可选）", expanded=True):
    auto_search = st.checkbox("自动联网搜索（先搜再回答）", value=True)
    search_k = st.slider("每次搜索条数", 3, 10, 5, 1)

st.sidebar.caption("提示：使用 itedus.cn 时，Base URL 设为 https://apis.itedus.cn/v1 即可。")

# --- Header ---
st.title("🤖 Agent7 Web")
st.caption("像聊天一样下指令，它会自动去做（带记忆 & 联网搜索 & 工具调用记录）")

# --- Session State ---
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, str]] = [{"role": "system", "content": ""}]
if "chat_display" not in st.session_state:
    st.session_state.chat_display: List[Dict[str, str]] = []

# --- 初始化适配器 ---
adapter = AgentAdapter(base_url=base_url, api_key=api_key, model=model, system_prompt=system_prompt)

# 若切换了 system prompt 或关闭记忆，需要重置对话
def reset_dialog():
    st.session_state.history = [{"role": "system", "content": system_prompt if keep_memory else ""}]
    st.session_state.chat_display = []

# 在侧边栏提供重置按钮
with st.sidebar:
    if st.button("🧹 清空/重置对话"):
        reset_dialog()
        st.experimental_rerun()

# 首次进入时，确保 system prompt 已设置
if st.session_state.history and st.session_state.history[0].get("content", "") != (system_prompt if keep_memory else ""):
    reset_dialog()

# --- 渲染历史聊天气泡 ---
for m in st.session_state.chat_display:
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        st.markdown(m["content"])

# --- 输入框 ---
placeholder = "和 Agent 说句话吧，例如：查下最近AI新闻、明早8点提醒我吃药"
user_text = st.chat_input(placeholder)

if user_text:
    # 1) 显示用户消息
    st.session_state.chat_display.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # 2) 调 Agent
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            out: AgentOutput = adapter.chat(
                st.session_state.history,
                user_text,
                auto_search=auto_search,
                search_k=search_k
            )
        st.markdown(out.text)
        if show_latency:
            st.caption(f"⏱️ {out.latency_ms} ms")
        if show_tools and out.tool_calls:
            st.markdown("**🔧 工具调用记录（含原始返回）**")
            st.json(out.tool_calls)

    # 3) 更新历史
    if keep_memory:
        st.session_state.history.append({"role": "user", "content": user_text})
        st.session_state.history.append({"role": "assistant", "content": out.text})
    else:
        st.session_state.history = [{"role": "system", "content": system_prompt}]

    st.session_state.chat_display.append({"role": "assistant", "content": out.text})
