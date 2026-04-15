"""
LLM API调用封装
支持OpenAI、阿里云百炼(DashScope)等兼容OpenAI格式的API
"""

import os
from typing import Optional
from openai import OpenAI

# 常用API配置
API_CONFIGS = {
    "openai": {
        "base_url": None,  # 使用默认
        "model": "gpt-4o-mini",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-72B-Instruct",
    },
}


class LLMClient:
    """LLM客户端封装，统一处理API调用"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: str = "openai",
    ):
        config = API_CONFIGS.get(provider, API_CONFIGS["openai"])
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", os.getenv("DASHSCOPE_API_KEY", ""))
        self.model = model or config["model"]
        self.provider = provider
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url or config["base_url"],
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = "你是一个专业的AI助手。",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成文本回复"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"API调用失败: {str(e)}"

    def generate_stream(self, prompt: str, system_prompt: str = "你是一个专业的AI助手。", temperature: float = 0.7):
        """流式生成文本，返回generator"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"API调用失败: {str(e)}"


def get_client() -> LLMClient:
    """获取全局LLM客户端实例"""
    return LLMClient()
