"""晴红AI OpenAI 兼容客户端。"""

from __future__ import annotations

import json
import re
import time

import requests


class QinghongAIError(Exception):
    """带可读说明的 AI 调用错误。"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class QinghongAIClient:
    def __init__(self, base_url: str, api_key: str, model: str = "gpt-4o-mini", timeout: int = 30):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model or "gpt-4o-mini"
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    def chat_messages(self, messages: list[dict], retries: int = 1) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                self._raise_for_status(resp)
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return self._extract_json(content)
            except QinghongAIError:
                raise
            except requests.exceptions.Timeout as exc:
                last_error = exc
                if attempt >= retries:
                    raise QinghongAIError("网络超时，请检查网络或稍后重试") from exc
            except requests.exceptions.ConnectionError as exc:
                last_error = exc
                if attempt >= retries:
                    raise QinghongAIError("无法连接 API 地址，请检查地址是否正确") from exc
            except (KeyError, IndexError, json.JSONDecodeError) as exc:
                raise QinghongAIError("API 返回格式异常，请检查模型是否支持对话接口") from exc
            except Exception as exc:
                last_error = exc
                if attempt >= retries:
                    raise QinghongAIError(f"AI 请求失败: {exc}") from exc
            if attempt < retries:
                time.sleep(0.8)
        raise QinghongAIError(f"AI 请求失败: {last_error}")

    def chat(self, prompt: str) -> str:
        """兼容旧接口：单条 user 消息。"""
        return self.chat_messages([{"role": "user", "content": prompt}])

    def test_connection(self) -> tuple[bool, str]:
        if not self.available:
            return False, "请先填写 API 地址与 Key"
        try:
            messages = [{"role": "user", "content": "请只回复两个字母：OK"}]
            content = self.chat_messages(messages, retries=0)
            preview = (content or "").strip()[:80]
            return True, f"连接成功（模型 {self.model}）\n响应：{preview or 'OK'}"
        except QinghongAIError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, f"连接失败: {exc}"

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.ok:
            return
        status = resp.status_code
        detail = ""
        try:
            body = resp.json()
            detail = body.get("error", {}).get("message") or body.get("message") or ""
        except Exception:
            detail = resp.text[:200] if resp.text else ""

        if status == 401:
            raise QinghongAIError("API Key 无效或已过期，请重新填写", status)
        if status == 403:
            raise QinghongAIError("无权访问该模型或接口，请检查 Key 权限", status)
        if status == 429:
            raise QinghongAIError("请求过于频繁或余额不足，请稍后重试或充值", status)
        if status >= 500:
            raise QinghongAIError(f"服务端异常（HTTP {status}），请稍后重试", status)
        msg = detail or f"HTTP {status}"
        raise QinghongAIError(f"API 错误：{msg}", status)

    @staticmethod
    def _extract_json(content: str) -> str:
        content = content.strip()
        if content.startswith("{"):
            return content
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            return match.group()
        return content
