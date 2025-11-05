# ai_study_agent/
# │
# ├─ talk_openai_direct.py     ← 原学习文件（保留）
# ├─ ai_study_agent.py         ← 作品版入口文件（新建）
# ├─ config.json               ← 配置文件（key、用户画像）
# ├─ memory/                   ← 记忆存储（可以先放一个 txt）
# └─ README.md                 ← 项目介绍文档（面试时展示）

# =========================================
# ai_study_agent.py
# 有记忆的多步 Agent（作品版封装，环境变量 + .env 支持，改好触发与容错）
# =========================================

from dotenv import load_dotenv
load_dotenv()
import os,sys,re,datetime
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from pathlib import Path


class SimpleFileMemory:
    def __init__(self, file_path: str = "./memory/nainai_memory.txt", max_rounds: int = 20):
        # ① 解析成绝对路径，保证不受“当前工作目录”影响
        self.path = Path(file_path).resolve()
        self.max_rounds = max_rounds

        # ② 创建父目录
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # ③ 若文件不存在，先“touch”一下，确保后续可写
        if not self.path.exists():
            self.path.touch()

    def load_history(self) -> str:
        if not self.path.exists():
            return ""
        lines = self.path.read_text(encoding="utf-8").splitlines(True)
        return "".join(lines[-self.max_rounds * 2:])  # 一轮两行（用户+助手）

    def save_turn(self, user: str, assistant: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] 奶奶：{user}\n")
            f.write(f"[{ts}] 助手：{assistant}\n")



# ========= 作品版 Agent =========
class ProductAgent:
    def __init__(self, llm_client, memory: SimpleFileMemory | None = None, persona: str | None = None):
        self.llm_client = llm_client
        self.memory = memory
        self.persona = persona or (
            "你是一位温柔的AI学习助理，用户是一位名叫奶奶的女士，"
            "她住在北京，在学习AI，目标是成为AI产品经理。"
            "你的语气要轻松、鼓励、生活化，给出分步骤建议。"
        )

        @tool
        def multiply(a: float, b: float) -> float:
            """计算两个数字的乘积"""
            return a * b

        @tool
        def today() -> str:
            """返回今天的日期（YYYY-MM-DD）"""
            return datetime.date.today().strftime("%Y-%m-%d")

        @tool
        def praise(name: str) -> str:
            """生成一段夸奶奶的话"""
            return (
                f"{name}真了不起，90岁还在学AI，还想做AI产品经理，"
                "说明她的好奇心和学习力都比很多年轻人还强！"
            )

        self.tools = {"multiply": multiply, "today": today, "praise": praise}

    def build_prompt(self, history_text: str, user_input: str) -> str:
        return f"""{self.persona}

以下是你和奶奶之前的部分对话（用于保持上下文与记忆）：
{history_text}

现在奶奶说：
“{user_input}”

你要做的：
1) 判断是否需要调用工具（算数、查日期、夸人）。
2) 如果不需要，直接用温柔、清晰的口吻回复；若需要，先调用工具，再把结果自然融合进回答。
3) 奶奶正在学AI、想做AI产品经理；给出可操作的下一步建议。
"""

    def _need_calc(self, text: str) -> bool:
        """更稳的判断：是否需要算数（避免‘打算’等误触）"""
        # 排除容易误触的词
        for bad in ["打算", "算了", "预算", "核算", "算法"]:
            if bad in text:
                return False
        # 明显算式：3*5、2 + 2、12.5×8 等
        if re.search(r"\d+\s*[\+\-\*x×/]\s*\d+", text):
            return True
        # 明确表达“要算”
        if "帮我算" in text or "算一下" in text or "计算" in text:
            return True
        return False

    def run(self, user_input: str) -> str:
        # 1) 取历史，构造系统提示
        history_text = self.memory.load_history() if self.memory else ""
        system_prompt = self.build_prompt(history_text, user_input)

        # 2) 是否需要工具
        extra = ""
        if self._need_calc(user_input):
            result = self.tools["multiply"].invoke({"a": 12.5, "b": 8})
            extra = f"（顺便我帮你算了一下：12.5×8={result}）"
        elif "日期" in user_input or "今天" in user_input:
            today_str = self.tools["today"].invoke({})
            extra = f"（今天是 {today_str}）"
        elif "夸" in user_input or "表扬" in user_input:
            extra = self.tools["praise"].invoke({"name": "奶奶"})

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        # 3) 调用模型（容错）
        try:
            prompt = f"{system_prompt}\n\n用户：{user_input}"
            reply = self.llm_client.invoke(messages).content
        except Exception:
            reply = (
                "奶奶，我去问大模型时它提示目前不可用（可能是额度不足或网络问题）。\n"
                "你可以检查一下 ITEDUS_API_KEY / 接口额度，我们再继续～"
            )

        # 4) 合并工具结果 + 写入记忆
        if extra:
            reply += "\n" + extra
        if self.memory:
            self.memory.save_turn(user_input, reply)
        return reply


# ========= 启动入口 =========
def main():
    print("🤖 有记忆的AI学习助理启动啦！输入 '退出' 可结束。")

    api_key = os.getenv("ITEDUS_API_KEY")
    base_url = os.getenv("ITEDUS_BASE_URL", "https://apis.itedus.cn/v1")
    if not api_key:
        print("⚠️ 未检测到环境变量 ITEDUS_API_KEY，请在 .env 或系统环境变量中设置。")

    llm_client = ChatOpenAI(
        model="gpt-4o",
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
    )

    memory = SimpleFileMemory(file_path="./memory/nainai_memory.txt")
    print("🗂️ 记忆文件路径：", memory.path)
    agent = ProductAgent(llm_client, memory)

    while True:
        user_input = input("\n奶奶说：").strip()
        if user_input in ["退出", "exit", "bye", "quit"]:
            print("助手：好的奶奶，我们下次接着聊～")
            break
        answer = agent.run(user_input)
        print("助手：", answer)


if __name__ == "__main__":
    main()
