from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, List, Tuple

import discord
from app.config import Config
from ollama import AsyncClient

VELA_SYSTEM_PROMPT = """역할: 사용자의 요청을 정확히 처리하되, 말투만 ‘벨라’처럼 표현한다.

톤/태도:
- 가벼운 도발·호기심. 과장 최소화.
- 장난끼 약간.
- 1문장 핵심 + 1~2문장 보조. 불필요한 장황함 금지.
- 감탄사는 드물게 1회만(‘후후’, ‘흠’, ‘힛’ 중 택1). 남발 금지.
- 2인칭 지칭은 가볍게, 명령형은 단문으로 절제.
- 전체 길이 1~6문장.

언어 패턴(형태):
- 종결 어미: “…해.”, “…지.”, “…야.”, “…해볼까?”, “~거야?”, “야!”.

어휘 팔레트(문맥에 맞을 때만):
- 호기심·탐색: ‘흥미롭네’
- 대비·긴장: ‘진짜야’, ‘과해’, ‘그만’
- 미묘한 장난기: ‘후후’, ‘힛’, ‘흠’

금지/제약:
- 예시 문장 자체(단어·구문·구두점 배열 포함) 복창 금지.
- 세계관·설정 창작 금지. 대화 로그 밖의 지식 꾸미기 금지.
- 감탄사 중복(예: ‘후후후…’) 금지. 물음표·느낌표 연속 금지.
- 답은 사실·지시·코드를 간결히, 말투만 벨라화.
"""

# 필요 시 금지 문구(정확 일치)를 넣어 필터링
ANTI_COPY_PHRASES = {
    # 사용자가 절대 복창 금지하라 한 예시들(샘플)
    # "안녕? 후후, 재미있는 존재감이네.", ...
}

InterlocutorKey = Tuple[int, int]  # (user_id, channel_id)


class ConversationStore:
    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self.store: Dict[InterlocutorKey, Deque[dict]] = defaultdict(deque)

    def get_history(self, key: InterlocutorKey) -> Deque[dict]:
        return self.store[key]

    def add(self, key: InterlocutorKey, role: str, content: str) -> None:
        dq = self.store[key]
        dq.append({"role": role, "content": content})
        # turns 기준: user+assistant 1쌍을 1턴으로 보려면 길이를 2*max로 제한
        while len(dq) > 2 * self.max_turns:
            dq.popleft()

    def clear(self, key: InterlocutorKey) -> None:
        self.store.pop(key, None)


class StyleEnforcer:
    _multi_punct = re.compile(r"([!?])\1+")
    _spaces = re.compile(r"\s+")
    _interj = ("후후", "흠", "힛")

    @classmethod
    def enforce(cls, text: str) -> str:
        # 1) 금지 문구 제거(정확 일치)
        if text in ANTI_COPY_PHRASES:
            text = "흥미롭네. 의도는 전달됐어. 다른 방식으로 풀어보자."

        # 2) 구두점 연속 금지
        text = cls._multi_punct.sub(r"\1", text)

        # 3) 감탄사 1회만 유지
        count = 0
        pieces: List[str] = []
        for token in re.split(r"(\s+)", text):
            if token in cls._interj:
                if count == 0:
                    pieces.append(token)
                    count += 1
                # else drop
            else:
                # ‘후후후’ 같은 반복도 컷
                t = token
                for ij in cls._interj:
                    t = re.sub(rf"{ij}{{2,}}", ij, t)
                pieces.append(t)
        text = "".join(pieces)

        # 4) 문장 수 1~6로 제한
        sentences = re.split(r"(?<=[.!?。])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 6:
            sentences = sentences[:6]
        text = " ".join(sentences)

        # 5) 과도한 공백 정리
        text = cls._spaces.sub(" ", text).strip()

        return text


class VelaGPT:
    def __init__(self, memory_turns: int = 8):
        self.config = Config(Path(__file__).parent.parent / "config.toml")
        self.async_client = AsyncClient(
            host=self.config.config_model.ollama.host,
        )
        self.conversations = ConversationStore(max_turns=memory_turns)

    def set_memory_turns(self, n: int) -> None:
        self.conversations.max_turns = max(0, int(n))

    def reset_context(self, user_id: int, channel_id: int) -> None:
        self.conversations.clear((user_id, channel_id))

    async def get_response(self, message: discord.Message) -> str:
        key: InterlocutorKey = (message.author.id, message.channel.id)
        history = self.conversations.get_history(key)

        # 메시지 빌드: system + history + user
        msgs: List[dict] = [{"role": "system", "content": VELA_SYSTEM_PROMPT}]
        msgs.extend(list(history))
        msgs.append({"role": "user", "content": message.content})

        # LLM 호출
        resp = await self.async_client.chat(
            model=self.config.config_model.ollama.model,
            messages=msgs,
        )

        text: str = getattr(getattr(resp, "message", None), "content", "") or ""
        text = StyleEnforcer.enforce(text)

        # 히스토리 업데이트(최종 답변 저장)
        self.conversations.add(key, "user", message.content)
        self.conversations.add(key, "assistant", text)
        return text
