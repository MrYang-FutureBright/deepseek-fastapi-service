
import requests
import os
import logging
from fastapi import HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s-%(levelname)s-%(name)s-%(message)s"
)

logger = logging.getLogger(__name__)


def request_model(messages):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        logger.error(
            "DEEPSEEK_API_KEY not set, error_code=%s",
            503
        )
        raise HTTPException(
            status_code=503,
            detail="异常"
        )

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "deepseek-flash",
        "messages": messages,
        "stream": False,
        "max_tokens": 512,
        "thinking": {"type": "disabled"}
    }
    try:
        response = requests.post(
            url="https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()

    except requests.exceptions.Timeout as e:
        raise HTTPException(
            status_code=504,
            detail="等待 DeepSeek 响应超时，请稍后重试"
        ) from e
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail="请求失败"
        ) from e

    try:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise HTTPException(
            status_code=502,
            detail="返回异常"
        ) from e

    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(
            status_code=502,
            detail="上游响应无效"
        )

    return answer


class ChatSession:
    def __init__(self, system_prompt):
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]

    def ask(self, question):
        pending = self.messages + [
            {"role": "user", "content": question}
        ]

        answer = request_model(pending)

        if answer is None:
            raise HTTPException(
                status_code=502,
                detail="返回无效值"
            )

        self.messages = pending + [
            {"role": "assistant", "content": answer}
        ]

        return answer

    def clear_history(self):
        del self.messages[1:]


def main():
    s1 = ChatSession(
        "你是这方面的专家，请给出专业且直白的回答"
    )

    while True:
        question = input(
            "\n请输入问题 输入 /exit 退出，输入 /clear 清空历史\n"
        ).strip()

        if not question:
            print("问题不能为空")
            continue

        if question == "/exit":
            print("已退出大模型")
            break

        elif question == "/clear":
            s1.clear_history()
            print("已清除历史聊天")

        else:
            try:
                answer = s1.ask(question)

            except HTTPException as e:
                print(f"错误 {e.status_code}：{e.detail}")

            else:
                print(answer)


if __name__ == "__main__":
    main()
