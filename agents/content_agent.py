"""
AIGC营销内容生成Agent
支持基于用户分层的个性化内容生成，每个变体附带假设
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client import LLMClient
from core.prompt_templates import get_template, list_templates
from core.data_models import StrategyResult, Variant, ContentResult


class ContentAgent:
    """AIGC内容生成Agent"""

    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()
        self.iteration_history = []

    def generate_content(
        self,
        template_key: str,
        params: dict,
        iterations: int = 1,
    ) -> str:
        """生成营销内容（兼容旧接口）"""
        from core.prompt_templates import get_template, PROMPT_TEMPLATES

        template = get_template(template_key)
        # Auto-fill missing template params with sensible defaults
        required_params = set()
        import re
        for m in re.finditer(r'\{(\w+)\}', template["template"]):
            required_params.add(m.group(1))

        defaults = {
            "email_purpose": "推广产品功能，提升用户活跃度",
            "target_audience": params.get("target_audience", "目标用户"),
            "key_message": params.get("key_message", params.get("product_name", "产品核心价值")),
            "offer": params.get("offer", "限时免费体验"),
            "product": params.get("product_name", params.get("product", "我们的产品")),
            "key_features": params.get("key_features", "高效、易用、专业"),
            "usage_scenario": params.get("usage_scenario", "日常工作场景"),
            "product_name": params.get("product_name", "产品"),
            "purpose": params.get("purpose", "社群互动"),
            "key_content": params.get("key_content", "产品更新通知"),
            "need_interaction": params.get("need_interaction", "是"),
            "article_topic": params.get("article_topic", "行业洞察"),
            "key_points": params.get("key_points", "核心观点"),
            "style": params.get("style", "专业深度"),
            "video_topic": params.get("video_topic", "产品介绍"),
            "duration": params.get("duration", "60"),
            "campaign_goal": params.get("campaign_goal", "品牌曝光"),
            "budget": params.get("budget", "中等预算"),
            "tutorial_topic": params.get("tutorial_topic", "使用教程"),
            "survey_goal": params.get("survey_goal", "用户满意度"),
            "key_questions": params.get("key_questions", "产品体验"),
            "length": params.get("length", "10"),
        }

        for param in required_params:
            if param not in params:
                params[param] = defaults.get(param, "")

        template = get_template(template_key)
        prompt = template["template"].format(**params)
        system = template["system"]

        result = self.client.generate(prompt, system_prompt=system)
        self.iteration_history = [{"iteration": 1, "content": result}]

        for i in range(2, iterations + 1):
            refine_prompt = f"""以下是上一版生成的内容，请进行优化改进：

要求：
1. 保持原有风格和结构
2. 让语言更有感染力和吸引力
3. 优化表达不够自然的地方
4. 确保内容充实，不要过于简短

上一版内容：
{result}

请输出优化后的版本："""

            result = self.client.generate(refine_prompt, system_prompt=system)
            self.iteration_history.append({"iteration": i, "content": result})

        return result

    def generate_for_segment(
        self,
        strategy: StrategyResult,
        segment_profile: str = "",
        problem_stage: str = "",
        variant_count: int = 3,
    ) -> ContentResult:
        """
        基于增长策略和用户分层生成内容变体
        每个变体附带一个可验证的假设

        Args:
            strategy: 策略推荐结果
            segment_profile: 用户画像描述
            problem_stage: 漏斗问题环节
            variant_count: 生成变体数量

        Returns:
            ContentResult: 包含多个内容变体和假设
        """
        template_keys = strategy.selected_templates if strategy.selected_templates else ["email_marketing"]

        variants = []
        hypotheses = [
            "社交证明型：展示其他用户的成功故事能增加信任感",
            "紧迫感型：限时/限量信息能促使立即行动",
            "帮助导向型：提供具体解决方案比推销更有效",
            "利益驱动型：直接展示产品价值比功能描述更有吸引力",
            "情感共鸣型：情感化表达比理性分析更能打动用户",
        ]

        for i in range(min(variant_count, len(hypotheses))):
            template = get_template(template_keys[0])

            prompt = f"""请生成一份营销内容：

【目标用户】
{segment_profile}

【问题场景】
用户在{problem_stage}环节流失

【策略指导】
- 活动类型：{strategy.campaign_type}
- 信息框架：{strategy.message_framework}
- 语气：{strategy.tone_guidance}
- CTA建议：{strategy.cta_recommendation}

【本版本假设】
{hypotheses[i]}

【要求】
1. 内容要针对上述用户画像和问题场景
2. 语气和风格严格按照策略指导
3. 包含明确的CTA
4. 内容格式适配{template['name']}平台
5. 内容必须充实完整，不少于150字
6. 包含具体的细节和案例，不要只写空泛的描述
7. 开头要有吸引力的钩子，结尾要有明确的行动引导"""

            content = self.client.generate(
                prompt, system_prompt=template["system"], max_tokens=2048
            )

            variants.append(Variant(
                version=f"版本{i+1} - {hypotheses[i].split('：')[0]}",
                content=content,
                hypothesis=hypotheses[i],
            ))

        # Build AB setup recommendation
        if len(variants) >= 3:
            ab_setup = (
                f"建议对比'{variants[0].version}'和'{variants[2].version}'进行A/B测试，"
                f"分别验证{hypotheses[0].split('：')[0]}与{hypotheses[2].split('：')[0]}的假设效果。"
                f"推荐样本量每组不少于100用户，测试周期7天。"
            )
        elif len(variants) >= 2:
            ab_setup = (
                f"建议对比'{variants[0].version}'和'{variants[1].version}'进行A/B测试。"
                f"推荐样本量每组不少于100用户，测试周期7天。"
            )
        else:
            ab_setup = "建议生成至少3个内容变体以进行有效的A/B测试。"

        return ContentResult(
            variants=variants,
            recommended_ab_setup=ab_setup,
            personalization_rules="在发送时替换{user_name}为用户实际名称，{design_count}为用户已创建设计数",
        )

    def get_available_templates(self) -> list:
        """获取可用模板列表"""
        return list_templates()
