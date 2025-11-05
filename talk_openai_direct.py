# proxies = {
#     "http": "http://127.0.0.1:7890",
#     "https": "http://127.0.0.1:7890",
# }

# headers = {
#     "Authorization": f"Bearer {API_KEY}",
#     "Content-Type": "application/json",
# }

# data = {
#     "model": "gpt-4o",
#     "messages": [
#         {"role": "user", "content": "夸夸90岁的奶奶"}
#     ],
# }

# print("① 请求准备好了")
# try:
#     resp = requests.post(
#         URL,
#         headers=headers,
#         json=data,
#         proxies=proxies,
#         timeout=20,           # 20 秒超时，卡住也最多20秒
#     )
#     print("② 收到响应，状态码：", resp.status_code)
#     print("③ 内容：", resp.text[:800])
# except requests.exceptions.ConnectTimeout:
#     print("❌ 连接超时（大概率是代理没把 apis.itedus.cn 放出来）")
# except requests.exceptions.ReadTimeout:
#     print("❌ 读超时（对面收到了但没回，可能是接口本身慢）")
# except Exception as e:
#     print("❌ 其他错误：", repr(e))



from dotenv import load_dotenv
load_dotenv()
import os
API_KEY = os.getenv("ITEDUS_API_KEY")
BASE_URL = os.getenv("ITEDUS_BASE_URL", "https://apis.itedus.cn/v1")

# --- 安全检查：如果没有读取到密钥就立即报错 ---
if not API_KEY:
    raise RuntimeError("❌ 缺少 ITEDUS_API_KEY，请在 .env 或系统环境变量中设置。")


import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory


# =====================================================
# 🧱 方法一：手动用 requests 调用接口

# 请求-等待-回应三步走
# =====================================================
def call_by_requests():
    URL = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "夸夸90岁的奶奶"}
        ],
    }

    print("① 准备发请求（requests版）...")
    try:
        resp = requests.post(URL, headers=headers, json=data, timeout=20)
        print("② 状态码：", resp.status_code)
        print("③ GPT 回复：")
        print(resp.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print("❌ 出错啦：", e)



# =====================================================
# 🧠 方法二：用 LangChain 封装好的方式调用接口
# longchain自动帮我完成
# 底层其实还是调用OpenAI接口，只是帮我们管理请求、记忆和多轮对话
# =====================================================
def call_by_langchain():
    URL = f"{BASE_URL}/chat/completions"

    # LangChain 内部也会发请求，但它帮我们封装好了
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL  # 用你的代理接口
    )

    print("① 准备发请求（LangChain版）...")
    resp = llm.invoke("夸夸90岁的奶奶")
    print("② GPT 回复：")
    print(resp.content)


# =====================================================
# 🧠 方法三：LangChain 封装 + PromptTemplate 模板化
# =====================================================
def call_by_langchain_prompt():
    URL = f"{BASE_URL}/chat/completions"

    # 1️⃣ 创建模型对象
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL
    )

    # 2️⃣ 创建 Prompt 模板
    # 模板中留出两个变量：person（人）和 age（年龄）
    template = "请用三句话夸夸{person}，她今年{age}岁了。"
    prompt = PromptTemplate.from_template(template)

    # 3️⃣ 使用变量填充模板
    final_prompt = prompt.format(person="奶奶", age=90)

    print("① 生成的 Prompt：")
    print(final_prompt)

    # 4️⃣ 把生成的 Prompt 发给模型
    print("\n② LangChain + PromptTemplate 发请求...")
    resp = llm.invoke(final_prompt)

    # 5️⃣ 打印输出结果
    print("③ GPT 回复：")
    print(resp.content)



# =====================================================
# 🧠 方法四：LangChain 封装 + PromptTemplate 模板化 + Memory记忆功能
# =====================================================
# 用一个简单的“内存仓库”来存每个对话的历史
# 实际项目里会存到数据库，这里我们先存在内存里就行
STORE = {}  # {session_id: ChatMessageHistory()}


def get_history(session_id: str) -> ChatMessageHistory:
    """根据会话ID拿到对应的历史，没有就新建一个。"""
    if session_id not in STORE:
        STORE[session_id] = ChatMessageHistory()
    return STORE[session_id]


def call_with_memory():
    URL = f"{BASE_URL}/chat/completions"

    # 1️⃣ 模型
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    # 2️⃣ 提示词（system + human，注意是 ChatPromptTemplate）
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个会哄90岁奶奶开心的AI助手，说话要温柔。"),
        ("human", "{input}"),
    ])

    # 3️⃣ 把 prompt 和 llm 串起来，形成一个“可运行的链”
    chain = prompt | llm

    # 4️⃣ 用 RunnableWithMessageHistory 给这条链加“记忆功能”
    #    这就是 1.x 推荐的“有记忆的对话”写法
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_history,   # 告诉它：历史在哪儿取
        input_messages_key="input",     # human 输入的字段名
        history_messages_key="history", # 存历史的字段名（固定这么写就行）
    )

    # 我们假设是同一个奶奶在聊天，用同一个 session_id
    session_id = "grandma-001"

    # 5️⃣ 连续聊三句，看看它记不记得
    print("=== 第1轮 ===")
    result1 = chain_with_history.invoke(
        {"input": "我叫奶奶，我今年90岁啦～"},
        config={"configurable": {"session_id": session_id}},
    )
    print("AI：", result1.content)

    print("\n=== 第2轮 ===")
    result2 = chain_with_history.invoke(
        {"input": "我住在北京，你记住哈"},
        config={"configurable": {"session_id": session_id}},
    )
    print("AI：", result2.content)

    print("\n=== 第3轮 ===")
    result3 = chain_with_history.invoke(
        {"input": "我刚才说我住哪儿来着？"},
        config={"configurable": {"session_id": session_id}},
    )
    print("AI：", result3.content)


# =====================================================
# 方法五：LangChain + PromptTemplate + Chains（任务链）
# 把多个任务串联起来执行，比如：
# 「总结文本 → 改写成三行诗」
# =====================================================

def call_by_langchain_chains():
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate

    URL = f"{BASE_URL}/chat/completions"

    # 1️⃣ 模型
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    # 2️⃣ 第一步：总结任务
    summarize_prompt = PromptTemplate.from_template(
        "请用一句话总结以下文字的主要内容：{text}"
    )
    summarize_chain = summarize_prompt | llm  # 用“管道”连接模板和模型

    # 3️⃣ 第二步：改写成诗
    poem_prompt = PromptTemplate.from_template(
        "请把这句话改写成押韵的三行小诗：{summary}"
    )
    poem_chain = poem_prompt | llm

    # 4️⃣ 把两步串起来形成“任务链”
    chain = summarize_chain | poem_chain

    # 5️⃣ 执行
    print("\n=== 方式五：LangChain + Chains（任务链） ===")
    text = "奶奶每天早起学习AI编程，虽然刚开始不太懂，但她很有耐心。"
    print("输入文本：", text)

    result = chain.invoke({"text": text})
    print("\nAI 输出结果：")
    print(result.content)



# =====================================================
# 方法六：LangChain + PromptTemplate + Chains + Memory
# 场景：先跟奶奶聊几句，记住奶奶的信息，
#      然后根据记住的内容写一首关于奶奶的小诗
# 适配你的版本：langchain 1.0.3
# =====================================================
def call_by_langchain_chains_with_memory():
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.runnables import RunnableWithMessageHistory
    from langchain_community.chat_message_histories import ChatMessageHistory

    URL = f"{BASE_URL}/chat/completions"

    # 1️⃣ 模型
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    # 我们做一个简单的“内存仓库”
    STORE = {}

    def get_history(session_id: str):
        """给 RunnableWithMessageHistory 用的，按会话ID取历史"""
        if session_id not in STORE:
            STORE[session_id] = ChatMessageHistory()
        return STORE[session_id]

    # 2️⃣ 第一步：对话式提示词 —— 用来“收集/记住奶奶信息”
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个会哄90岁奶奶开心的AI助手，说话温柔，记住奶奶说过的话。"),
        ("human", "{input}"),
    ])

    # 3️⃣ 把这个聊天提示词接到模型上，得到“聊天链”
    chat_chain = chat_prompt | llm

    # 4️⃣ 给这个聊天链加上“记忆能力”
    chat_chain_with_memory = RunnableWithMessageHistory(
        chat_chain,
        get_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    # 我们用同一个会话ID，表示都是同一个奶奶在说话
    session_id = "grandma-001"

    print("\n=== 方式六：LangChain + Chains + Memory ===")

    # 5️⃣ 第1轮：奶奶先自我介绍
    r1 = chat_chain_with_memory.invoke(
        {"input": "我叫奶奶，今年90岁了，我住在北京，喜欢学AI。"},
        config={"configurable": {"session_id": session_id}},
    )
    print("AI（第1轮）：", r1.content)

    # 6️⃣ 第2轮：奶奶再补充一点信息
    r2 = chat_chain_with_memory.invoke(
        {"input": "我学AI是想以后去当产品经理，你记住哈。"},
        config={"configurable": {"session_id": session_id}},
    )
    print("AI（第2轮）：", r2.content)

    # 👉 到这里为止，“记忆里”已经有了：
    # - 奶奶90岁
    # - 住北京
    # - 喜欢学AI
    # - 想当产品经理

    # 7️⃣ 现在来第二条链：写诗链
    #    我们让模型“回看对话历史”，然后写一段关于奶奶的诗
    poem_prompt = PromptTemplate.from_template(
        "根据这段对话历史，写一首三行的夸赞诗，口吻要温柔：\n{history_text}"
    )

    # 这个写诗链也要用 llm
    poem_chain = poem_prompt | llm

    # 我们要把“历史消息”取出来变成文本，传给写诗链
    history = get_history(session_id)
    # history.messages 是一堆 HumanMessage / AIMessage，我们简单拼成一段文本
    history_text = ""
    for msg in history.messages:
        role = "用户" if msg.type == "human" else "AI"
        history_text += f"{role}：{msg.content}\n"

    print("\n--- 历史对话（给你看看模型能看到啥） ---")
    print(history_text)

    # 8️⃣ 调用写诗链
    poem_result = poem_chain.invoke({"history_text": history_text})
    print("\nAI 写的诗：")
    print(poem_result.content)


# =====================================================
# 🧠 方式七：LangChain Agent（智能体，多工具版）
# 场景：
#   - 奶奶给一句自然语言
#   - Agent 自己判断要不要先算数、要不要查日期、要不要写诗
#   - 最后再好好夸奶奶
# 说明：
#  # 思路：LLM 想 → 说要用哪个工具 → Python 真去调 → 再让 LLM 出最终答案
# =====================================================
def call_by_langchain_agent():
    import datetime
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    URL = f"{BASE_URL}/chat/completions"

    # 1️⃣ 模型
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0,   # 这里设 0 让它更听话
    )

    # 2️⃣ 我们自己定义几个“工具”（其实就是普通的 Python 函数）
    def tool_multiply(a: float, b: float) -> float:
        """计算两个数字的乘积"""
        return a * b

    def tool_today() -> str:
        """返回今天的日期 YYYY-MM-DD"""
        return datetime.date.today().strftime("%Y-%m-%d")

    def tool_praise(name: str) -> str:
        """生成一段夸奶奶的话"""
        return (
            f"{name}真了不起，90岁还在学AI，还想做AI产品经理，"
            "说明她的好奇心和学习力都比很多年轻人还强！"
        )

    # 3️⃣ 给大模型一条“Agent 提示词”——告诉它有哪些工具可以用
    planner_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个会调用工具的AI Agent。
你现在能用的工具有：
1. multiply(a, b): 计算两个数字的乘积
2. today(): 获取今天的日期
3. praise(name): 夸奖一位奶奶
请你根据用户的请求，先说出你要用哪个工具和参数，格式必须是 JSON，只能包含这两个key：
{{
  "tool": "<工具名，必须是 multiply / today / praise 之一>",
  "args": {{...}}
}}
只输出 JSON，不要多余文字。"""
        ),
        ("human", "{user_input}"),
    ])

    # 4️⃣ 用户这次的任务（我们让它必须用到至少一个工具）
    user_query = (
        "帮我查一下今天的日期，再算 12.5 * 8，最后夸夸叫“奶奶”的人，"
        "她住在北京、在学AI、想去做AI产品经理，把这些都说进去。"
    )

    print("\n=== 方式七：手写版 Agent ===")
    print("用户输入：", user_query)

    # 5️⃣ 先让模型“规划”——说它要用哪个工具
    planner_messages = planner_prompt.format_messages(user_input=user_query)
    planner_response = llm.invoke(planner_messages)
    planner_text = planner_response.content
    print("\n[Agent 规划阶段模型输出的 JSON]：")
    print(planner_text)

    # 6️⃣ 解析它说的 JSON（它说要用哪个工具我们就真去调哪个）
    import json
    try:
        plan = json.loads(planner_text)
    except json.JSONDecodeError:
        # 它要是没按要求说，就当它不会用工具
        plan = {"tool": None, "args": {}}

    tool_name = plan.get("tool")
    tool_args = plan.get("args", {})

    # 7️⃣ 真正调用工具
    tool_result = None
    if tool_name == "multiply":
        tool_result = tool_multiply(**tool_args)
    elif tool_name == "today":
        tool_result = tool_today()
    elif tool_name == "praise":
        tool_result = tool_praise(**tool_args)
    else:
        tool_result = "（没有调用工具，可能是模型没按要求输出）"

    print("\n[Python 实际调用工具的结果]：", tool_result)

    # 8️⃣ 再让模型把“用户原始需求 + 工具实际结果”综合成最后的回答
    final_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个会整理工具调用结果的AI，请用温柔的语气回答90岁的奶奶。"
        ),
        (
            "human",
            "用户的原始需求是：{user_input}\n"
            "你刚刚调用工具的结果是：{tool_result}\n"
            "请把日期、乘积结果、以及对奶奶的夸奖综合成一段温柔的话，别啰嗦。"
        ),
    ])

    final_messages = final_prompt.format_messages(
        user_input=user_query,
        tool_result=str(tool_result),
    )
    final_response = llm.invoke(final_messages)

    print("\nAgent 最终回答：")
    print(final_response.content)

# =====================================================
# 🧠 方式八：多步工具 Agent（无 langchain.agents 依赖版）
    # 相比你的方式七：
    # - 支持多次工具调用
    # - 每一步都能看到“模型的想法”
    # - 最后统一整理回复
    # """
# =====================================================
def call_by_langchain_official_agent():
    import datetime
    import json
    import re
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool

    URL = f"{BASE_URL}/chat/completions"

    # 小工具：从输出里剥离出纯 JSON
    def _extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"^```", "", text).strip()
            if text.endswith("```"):
                text = text[: -3].strip()
        return text

    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0,
    )

    @tool
    def multiply(a: float, b: float) -> float:
        """计算两个数字的乘积"""
        return a * b

    @tool
    def today() -> str:
        """返回今天的日期 YYYY-MM-DD"""
        return datetime.date.today().strftime("%Y-%m-%d")

    @tool
    def praise(name: str) -> str:
        """生成一段夸奶奶的话"""
        return (
            f"{name}真了不起，90岁还在学AI，还想做AI产品经理，"
            "说明她的好奇心和学习力都比很多年轻人还强！"
        )

    tools = {
        "multiply": multiply,
        "today": today,
        "praise": praise,
    }

    DECIDE_PROMPT = """你是一个会调用工具的智能体。你可以做多步推理。
你目前已经知道的内容是：
{context}

用户的原始目标是：
{user_input}

你可以使用的工具有（只能从里面选）：
- multiply(a, b): 计算两个数字的乘积
- today(): 获取今天的日期
- praise(name): 夸奖奶奶

如果你觉得还需要用工具，请输出一个 JSON（只输出 JSON）：
{{
  "action": "tool",
  "tool": "<工具名>",
  "args": {{...}}
}}

如果你觉得已经有足够信息可以回答了，请输出：
{{
  "action": "finish",
  "final": "<你要回答给用户的话的大纲>"
}}
只能输出 JSON，不能加 ``` 包裹，不能加文字。
"""

    FINAL_PROMPT = """你是一个温柔的AI，请根据下面的信息，写出最终要跟奶奶说的话，口吻温柔、简短：
用户原始需求：
{user_input}

你调用工具得到的中间信息：
{context}

请生成最终回答。"""

    def agent_run(user_input: str, max_steps: int = 4) -> str:
        context = []

        for step in range(max_steps):
            print(f"\n--- 第 {step+1} 步思考 ---")
            context_text = "\n".join(context) if context else "（目前还没有工具结果）"

            decide_msg = DECIDE_PROMPT.format(
                context=context_text,
                user_input=user_input,
            )
            decide_resp = llm.invoke(decide_msg)
            decide_text = decide_resp.content
            print("[模型决定输出]：", decide_text)

            # 👇 新增：先清洗再解析
            clean = _extract_json(decide_text)

            try:
                decide_obj = json.loads(clean)
            except json.JSONDecodeError:
                print("❌ 模型没按 JSON 格式来，提前结束。原文是：", decide_text)
                break

            action = decide_obj.get("action")

            if action == "finish":
                outline = decide_obj.get("final", "")
                context.append(f"[模型给的回答大纲] {outline}")
                break

            if action == "tool":
                tool_name = decide_obj.get("tool")
                tool_args = decide_obj.get("args", {})
                if tool_name not in tools:
                    context.append(f"[错误] 没有这个工具：{tool_name}")
                    break

                tool_fn = tools[tool_name]
                if tool_args:
                    tool_result = tool_fn.invoke(tool_args)
                else:
                    tool_result = tool_fn.invoke({})

                print(f"[Python 工具执行结果] {tool_name} → {tool_result}")
                context.append(f"[{tool_name}] {tool_result}")
            else:
                context.append(f"[错误] 未知动作：{action}")
                break

        final_msg = FINAL_PROMPT.format(
            user_input=user_input,
            context="\n".join(context),
        )
        final_resp = llm.invoke(final_msg)
        return final_resp.content

    # 🧪 测试
    user_query = (
        "帮我查一下今天的日期，再算 12.5 * 8，最后夸夸叫“奶奶”的人，"
        "她住在北京、在学AI、想去做AI产品经理，把这些都说进去。"
    )

    print("\n=== 方式八：多步工具 Agent（耐脏版） ===")
    print("用户输入：", user_query)
    answer = agent_run(user_query)
    print("\nAgent 最终回答：")
    print(answer)


# =====================================================
# 🧠 方式九：有记忆的多步 Agent
# 在方式八的基础上加入对话记忆（同一个 session 会记上一轮说过的话）
# =====================================================
def call_by_langchain_agent_with_memory():
    import datetime
    import json
    import re
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langchain_community.chat_message_histories import ChatMessageHistory

    URL = f"{BASE_URL}/chat/completions"

    # 1️⃣ 会话记忆仓库：session_id -> ChatMessageHistory
    STORE = {}

    def get_history(session_id: str) -> ChatMessageHistory:
        if session_id not in STORE:
            STORE[session_id] = ChatMessageHistory()
        return STORE[session_id]

    # 2️⃣ 模型
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0,
    )

    # 3️⃣ 工具（沿用方式八的三个）
    @tool
    def multiply(a: float, b: float) -> float:
        """计算两个数字的乘积"""
        return a * b

    @tool
    def today() -> str:
        """返回今天的日期 YYYY-MM-DD"""
        return datetime.date.today().strftime("%Y-%m-%d")

    @tool
    def praise(name: str) -> str:
        """生成一段夸奶奶的话"""
        return (
            f"{name}真了不起，90岁还在学AI，还想做AI产品经理，"
            "说明她的好奇心和学习力都比很多年轻人还强！"
        )

    tools = {
        "multiply": multiply,
        "today": today,
        "praise": praise,
    }

    # 4️⃣ 小工具：把 ```json ... ``` 剥成纯 JSON
    def extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"^```", "", text).strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        return text

    # 5️⃣ 决策提示：这次要把“历史对话”也塞进去
    DECIDE_PROMPT = """你是一个会调用工具的智能体，可以做多步推理。

以下是本次会话的历史内容（用户之前说过的话，可能要参考）：
{history_text}

以下是你目前已经拿到的中间工具结果：
{context}

用户这次的新目标是：
{user_input}

你可以使用的工具有（只能从下面选）：
- multiply(a, b): 计算两个数字的乘积
- today(): 获取今天的日期
- praise(name): 夸奖奶奶

如果你觉得还需要用工具，请输出一个 JSON（只能输出 JSON）：
{{
  "action": "tool",
  "tool": "<工具名>",
  "args": {{...}}
}}

如果你觉得已经可以给用户最终回答了，请输出：
{{
  "action": "finish",
  "final": "<你要说的内容大纲>"
}}
只能输出 JSON，不能加解释，也不要加 ``` 包裹。
"""

    # 6️⃣ 最终整理提示
    FINAL_PROMPT = """你是一个温柔的AI助手。请根据下面的信息，生成要跟奶奶说的话，语气温柔简短。

用户这次的请求：
{user_input}

这次对话中你得到的工具结果：
{context}

这位奶奶之前说过的话（历史）：
{history_text}

请写出最终回答。
"""

    # 7️⃣ Agent 主循环（多步 + 记忆）
    def agent_run(user_input: str, session_id: str = "grandma-001", max_steps: int = 4) -> str:
        # 7.1 取出这位奶奶之前的对话历史
        history_obj = get_history(session_id)
        if history_obj.messages:
            history_lines = []
            for msg in history_obj.messages:
                role = "用户" if msg.type == "human" else "AI"
                history_lines.append(f"{role}：{msg.content}")
            history_text = "\n".join(history_lines)
        else:
            history_text = "（暂无历史）"

        # 7.2 本轮的中间工具结果
        context = []

        for step in range(max_steps):
            print(f"\n--- 第 {step + 1} 步思考 ---")

            context_text = "\n".join(context) if context else "（还没有工具结果）"

            decide_input = DECIDE_PROMPT.format(
                history_text=history_text,
                context=context_text,
                user_input=user_input,
            )

            decide_resp = llm.invoke(decide_input)
            decide_text = decide_resp.content
            print("[模型决策输出]：", decide_text)

            clean = extract_json(decide_text)
            try:
                decide_obj = json.loads(clean)
            except json.JSONDecodeError:
                print("❌ 模型没按 JSON 来，提前结束。原文是：", decide_text)
                context.append("[错误] 模型输出不是合法 JSON")
                break

            action = decide_obj.get("action")

            if action == "finish":
                outline = decide_obj.get("final", "")
                context.append(f"[模型最终大纲] {outline}")
                break

            if action == "tool":
                tool_name = decide_obj.get("tool")
                tool_args = decide_obj.get("args", {})
                if tool_name not in tools:
                    context.append(f"[错误] 没有这个工具：{tool_name}")
                    break

                tool_fn = tools[tool_name]
                if tool_args:
                    tool_result = tool_fn.invoke(tool_args)
                else:
                    tool_result = tool_fn.invoke({})
                print(f"[工具执行结果] {tool_name} → {tool_result}")
                context.append(f"[{tool_name}] {tool_result}")
            else:
                context.append(f"[错误] 未知动作：{action}")
                break

        # 7.3 最终整理
        final_input = FINAL_PROMPT.format(
            user_input=user_input,
            context="\n".join(context),
            history_text=history_text,
        )
        final_resp = llm.invoke(final_input)
        final_answer = final_resp.content

        # 7.4 把这轮的问答写回历史
        history_obj.add_user_message(user_input)
        history_obj.add_ai_message(final_answer)

        return final_answer

    # 8️⃣ 模拟两轮对话，看看记不记得
    print("\n=== 方式九：有记忆的多步 Agent ===")

    # 第1轮：先告诉她信息
    ans1 = agent_run("我叫奶奶，今年90岁，住在北京，最近在学AI。")
    print("AI（第1轮）：", ans1)

    # 第2轮：考它还记不记得
    ans2 = agent_run("我刚才说我住哪来着？顺便再夸夸我～")
    print("AI（第2轮）：", ans2)







# =====================================================
# 🚀 程序入口
# =====================================================
if __name__ == "__main__":


    print("=== 方式一：requests ===")
    call_by_requests()

    print("\n=== 方式二：LangChain ===")
    call_by_langchain()

    print("\n=== 方式三：LangChain + PromptTemplate（结构化提示词） ===")
    call_by_langchain_prompt()

    print("\n=== 方式四：LangChain + PromptTemplate （结构化提示词）+ Memory ===")
    call_with_memory()

    print("\n=== 方式五：LangChain + Chains（任务链） ===")
    call_by_langchain_chains()

    print("\n=== 方式六：LangChain + Chains + Memory ===")
    call_by_langchain_chains_with_memory()

    print("\n=== 方式七：LangChain Agent（智能体） ===")
    call_by_langchain_agent()

    print("\n=== 方式八：LangChain Agent（智能体） ===")
    call_by_langchain_official_agent()

    print("\n=== 方式九：有记忆的多步 Agent ===")
    call_by_langchain_agent_with_memory()