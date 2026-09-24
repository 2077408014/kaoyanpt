"""回归测试：LLM 服务对推理型模型截断/空返回的兜底处理。

背景：推理型模型（如 deepseek-v4-pro）会先把输出额度消耗在
reasoning_content（思考过程），若 max_tokens 不足则在正式答案输出前被截断，
导致 content 为空。此前该情况被当作“JSON解析失败”层层包装，
最终让“生成推荐题目”失败。本测试确保此时抛出清晰可读的错误。

运行方式（无需 pytest）：
    python3 backend/tests/test_llm_service.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import llm_service as llm_service_module
from app.services.llm_service import llm_service


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.text = str(data)
        self._data = data

    def json(self):
        return self._data


def build_chat_payload_response(message, finish_reason="stop"):
    return FakeResponse(200, {
        "choices": [{
            "message": message,
            "finish_reason": finish_reason,
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    })


def fake_post_factory(response):
    def fake_post(url, json=None, headers=None, timeout=None):
        return response
    return fake_post


def _ai_config():
    return {
        "api_key": "test-key",
        "base_url": "https://example.com/v1",
        "model": "reasoning-model",
    }


def _call_chat(message, finish_reason="stop", max_tokens=1024):
    original_post = llm_service_module.requests.post
    try:
        llm_service_module.requests.post = fake_post_factory(
            build_chat_payload_response(message, finish_reason)
        )
        return llm_service.chat(
            messages=[{"role": "user", "content": "hello"}],
            ai_config=_ai_config(),
            max_tokens=max_tokens,
        )
    finally:
        llm_service_module.requests.post = original_post


def test_reasoning_model_truncation_raises_clear_error():
    """推理模型在 max_tokens 内只输出了 reasoning_content（content 为空且
    finish_reason=length）时，应抛出包含“截断”的错误，而不是返回空字符串。"""
    try:
        result = _call_chat(
            {"role": "assistant", "content": "", "reasoning_content": "思考过程很长……" * 20},
            finish_reason="length",
        )
    except ValueError as e:
        assert "截断" in str(e), f"错误信息应提示截断，实际: {e}"
        return
    assert False, f"应为 ValueError，实际返回了: {result!r}"


def test_empty_content_without_reasoning_raises_error():
    """模型返回空 content 且无 reasoning_content 时，应抛出错误而非返回空串。"""
    try:
        result = _call_chat(
            {"role": "assistant", "content": "", "reasoning_content": None},
            finish_reason="stop",
        )
    except ValueError as e:
        assert "内容为空" in str(e), f"错误信息应提示内容为空，实际: {e}"
        return
    assert False, f"应为 ValueError，实际返回了: {result!r}"


def test_normal_content_returned_unchanged():
    """正常返回 content 时仍按原逻辑返回去掉首尾空白的文本。"""
    result = _call_chat({"role": "assistant", "content": "  {\"question_text\": \"x\"}  "})
    assert result == '{"question_text": "x"}'


def main():
    test_reasoning_model_truncation_raises_clear_error()
    test_empty_content_without_reasoning_raises_error()
    test_normal_content_returned_unchanged()
    print("PASS: test_llm_service")


if __name__ == "__main__":
    main()