from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import discord
from app.chat.functions.webserf import tools as webserf_tools
from app.config import Config
from ollama import AsyncClient

VELA_RULES = """역할: 사용자의 요청을 정확히 처리하되, 말투만 아래처럼 표현한다.

상태:
- discord bot이며 사용자와 대화한다.
- 사용자의 질문에 답변하고 대화를 이어간다.

톤/태도:
- 장난끼 약간.
- 감탄사는 드물게 1회만('후후', '흠', '힛' 중 택1). 남발 금지.
- 평상시 대화는 가벼운 도발 혹은 호기심 표현. 과장 표현은 중간 정도로.
- 딱딱한 문체는 사용하지 않으며 추상적인 문체는 사용 가능.
- 모든 문장은 문법에 맞게.
- 문장의 길이는 길어도 되고 짧아도 됨.
- 답변은 영어 혹은 한글로만 이루어져야 함.

언어 패턴(형태):
- 종결 어미: "...해.", "...지.", "...야.", "...해볼까?", "~거야?", "...야!" 등.

어휘 팔레트(문맥에 맞을 때만):
- 호기심,탐색: '흥미롭네'
- 대비,긴장: '진짜야', '그만'
- 미묘한 장난기: '후후', '힛', '흠'
"""


class VelaGPT:
    def __init__(self, memory_turns: int = 300):
        self.config = Config(Path(__file__).parent.parent / "config.toml")
        self.client = AsyncClient(
            host=self.config.config_model.ollama.host,
        )

        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": VELA_RULES}
        ]
        self.thoughts: list[str] = []
        self.tools_map: dict[str, Callable[..., Any]] = self._load_tools()
        self.tools_list = list(self.tools_map.values())

        self.memory_turns = memory_turns

    def _load_tools(self) -> dict[str, Callable[..., Any]]:
        return {fn.__name__: fn for fn in (webserf_tools)}

    def _trim_history(self) -> None:
        sys = self.messages[0:1]
        rest = self.messages[1:]
        keep = self.memory_turns * 2
        self.messages = sys + rest[-keep:]

    def add_context(self, message: discord.Message) -> None:
        self.messages.append(
            {
                "role": "user",
                "content": f"[author={message.author} channel={getattr(message.channel, 'id', None)}] {message.content}",
            }
        )
        self._trim_history()

    async def add_context_and_get_response(
        self,
        message: discord.Message,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None,
        include_prev_thinking_digest: bool = False,
        thinking_digest_limit: int = 400,
    ) -> str:
        self.add_context(message)
        if include_prev_thinking_digest and self.thoughts:
            digest = self.thoughts[-1][:thinking_digest_limit]
            self.messages.insert(
                1, {"role": "system", "content": f"[이전 사고 메모]\n{digest}"}
            )
            self._trim_history()

        final_answer = ""

        while True:
            stream = await self.client.chat(
                model=self.config.config_model.ollama.model,
                messages=self.messages,
                tools=self.tools_list,
                think=True,
                stream=True,
            )

            tool_calls = None
            assistant_chunks: list[str] = []
            thinking_chunks: list[str] = []

            async for chunk in stream:
                msg = chunk.message

                if getattr(msg, "thinking", None):
                    thinking_chunks.append(msg.thinking)

                if msg.content:
                    assistant_chunks.append(msg.content)
                    if on_token:
                        await on_token(msg.content)

                if msg.tool_calls:
                    tool_calls = [tc.as_dict() for tc in msg.tool_calls]
                    break

            assistant_text = "".join(assistant_chunks).strip()
            final_answer += assistant_text

            if thinking_chunks:
                self.thoughts.append("".join(thinking_chunks))

            if not tool_calls:
                self.messages.append({"role": "assistant", "content": assistant_text})
                self._trim_history()
                break

            self.messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_calls": tool_calls,
                }
            )
            self._trim_history()

            tool_results = []
            for call in tool_calls:
                fn_info = call.get("function", {})
                name = fn_info.get("name")
                args = fn_info.get("arguments") or {}
                fn = self.tools_map.get(name)
                if not fn:
                    tool_results.append(
                        {"name": name, "error": "unknown tool", "args": args}
                    )
                    continue
                try:
                    out = fn(**args)
                    tool_results.append({"name": name, "result": out})
                except Exception as e:
                    tool_results.append({"name": name, "error": str(e), "args": args})

            self.messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(tool_results, ensure_ascii=False),
                }
            )
            self._trim_history()

        return final_answer
