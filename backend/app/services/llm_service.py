import requests
import json
import re
from typing import Optional, List, Dict, Any
from ..core.config import settings


class LLMService:
    def __init__(self):
        self.timeout = settings.AI_TIMEOUT
        self.max_tokens = settings.AI_MAX_TOKENS

    def _build_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/chat/completions"

    def _extract_json(self, text: str) -> Optional[Any]:
        cleaned = text.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue

        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        bracket_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if bracket_match:
            try:
                return json.loads(bracket_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not ai_config.get("api_key"):
            raise ValueError("API Key 未配置，请先在AI配置页面设置")

        url = self._build_url(ai_config["base_url"])
        payload = {
            "model": ai_config["model"],
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ai_config['api_key']}",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                error_detail = response.text[:500]
                print(f"[LLM] HTTP {response.status_code}: {error_detail}")
                if response.status_code == 401:
                    raise ValueError("API Key 无效或已过期，请检查AI配置")
                elif response.status_code == 404:
                    raise ValueError("API 地址不存在，请检查 Base URL 和模型名称")
                elif response.status_code == 429:
                    raise ValueError("请求过于频繁，请稍后再试")
                else:
                    raise ValueError(f"AI 服务调用失败（HTTP {response.status_code}）")
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            raise ValueError("AI 服务请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            raise ValueError("无法连接到 AI 服务，请检查网络和 Base URL")
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"AI 服务调用失败：{str(e)}")

    def chat_single_turn(
        self,
        user_message: str,
        ai_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages, ai_config, temperature, max_tokens)

    def chat_with_history(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        ai_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for msg in history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages, ai_config, temperature, max_tokens)

    def generate_json(
        self,
        user_message: str,
        ai_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        max_retries: int = 1,
        schema_hint: Optional[str] = None,
    ) -> Any:
        retry_system = system_prompt or "你是一个专业的AI助手，负责生成结构化数据。"

        if schema_hint:
            retry_system += f"\n\n输出必须是严格的JSON格式，结构如下：\n{schema_hint}\n\n重要：所有字段必须填充有效内容，不能为空字符串！只输出JSON，不要任何其他文字、解释或markdown标记。"

        current_system = retry_system
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = self.chat_single_turn(
                    user_message=user_message,
                    ai_config=ai_config,
                    system_prompt=current_system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                parsed = self._extract_json(result)
                if parsed is not None:
                    return parsed

                last_error = "返回内容无法解析为JSON"
                print(f"[LLM] JSON解析失败，尝试 {attempt + 1}/{max_retries + 1}")

                if attempt < max_retries:
                    current_system = (
                        f"{retry_system}\n\n"
                        f"重要：上一次你的输出格式不正确，无法被解析为JSON。"
                        f"请严格按照要求输出纯JSON，不要添加任何额外文字，"
                        f"不要用代码块包裹，不要有解释说明。"
                    )

            except ValueError as ve:
                raise ve
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    continue
                raise ValueError(f"AI生成失败：{last_error}")

        raise ValueError(f"AI返回格式异常，无法解析为JSON（已重试{max_retries}次）")


llm_service = LLMService()