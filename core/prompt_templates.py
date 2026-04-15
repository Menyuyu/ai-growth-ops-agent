"""
Prompt模板库
覆盖小红书、抖音、公众号等多平台营销场景
"""

PROMPT_TEMPLATES = {
    # ========== 小红书文案 ==========
    "xiaohongshu": {
        "name": "小红书种草文案",
        "system": "你是一个资深小红书内容运营，擅长写爆款种草文案。风格：真实、亲切、有吸引力。多用emoji，善用分段和标签。",
        "template": """请为以下产品/服务写一篇小红书种草文案：

产品/服务：{product}
目标人群：{target_audience}
核心卖点：{key_features}
使用场景：{usage_scenario}

要求：
1. 标题要吸引眼球，控制在20字以内
2. 正文300-500字，分段落写
3. 多用emoji增加可读性
4. 结尾加上3-5个相关话题标签
5. 语气真实自然，像一个真实用户分享体验""",
    },
    "xiaohongshu_tutorial": {
        "name": "小红书教程文案",
        "system": "你是一个小红书知识博主，擅长写干货教程类内容。风格：专业但不枯燥，步骤清晰。",
        "template": """请写一篇小红书教程文案：

教程主题：{tutorial_topic}
目标人群：{target_audience}
核心知识点：{key_points}

要求：
1. 标题要有数字或结果导向（如"3步学会XX"）
2. 正文按步骤分点写，每步简短明了
3. 适当加入避坑提示
4. 结尾引导收藏和关注
5. 总字数400-600字""",
    },
    # ========== 抖音短视频 ==========
    "douyin_script": {
        "name": "抖音短视频脚本",
        "system": "你是一个抖音短视频编导，擅长写爆款短视频脚本。",
        "template": """请为一个短视频写分镜头脚本：

视频主题：{video_topic}
目标人群：{target_audience}
核心信息：{key_message}
视频时长：{duration}秒

要求：
1. 按"开头钩子-中间内容-结尾CTA"结构
2. 列出每个镜头的画面描述+台词+时长
3. 开头3秒必须有钩子吸引注意力
4. 结尾要有明确的行动引导
5. 总台词量控制在{duration * 4}字以内""",
    },
    "douyin_live": {
        "name": "抖音直播话术",
        "system": "你是一个抖音直播运营，擅长写直播带货话术。",
        "template": """请为一场直播带货写话术脚本：

直播产品：{product}
产品卖点：{key_features}
目标人群：{target_audience}
直播时长：{duration}分钟

要求：
1. 包含开场暖场、产品讲解、互动环节、逼单环节
2. 每个环节写出具体的话术
3. 加入互动引导（扣1、点关注等）
4. 加入紧迫感营造（限时、限量等）
5. 总字数800-1200字""",
    },
    # ========== 公众号 ==========
    "wechat_article": {
        "name": "公众号推文",
        "system": "你是一个微信公众号内容运营，擅长写深度长文。",
        "template": """请写一篇公众号推文：

文章主题：{article_topic}
目标人群：{target_audience}
核心观点：{key_points}
文章风格：{style}

要求：
1. 标题要有吸引力，可参考"痛点+解决方案"模式
2. 开头要有故事或案例引入
3. 正文分段论述，每段有小标题
4. 适当引用数据或研究支撑观点
5. 结尾要有总结和行动引导
6. 总字数1500-2500字""",
    },
    "wechat_title": {
        "name": "公众号标题生成",
        "system": "你是一个爆款标题专家。",
        "template": """请为以下文章生成10个爆款公众号标题：

文章主题：{article_topic}
核心内容：{key_content}

要求：
1. 涵盖不同类型的标题：痛点型、悬念型、数字型、对比型、情感型
2. 每个标题控制在25字以内
3. 标注每个标题的类型
4. 选出你认为最好的3个并说明理由""",
    },
    # ========== 电商文案 ==========
    "ecommerce_product": {
        "name": "电商产品详情页文案",
        "system": "你是一个电商文案专家，擅长写高转化的产品详情页。",
        "template": """请为以下产品写详情页文案：

产品名称：{product_name}
产品卖点：{key_features}
目标人群：{target_audience}
竞品差异：{differentiation}

要求：
1. 写一个吸引眼球的Slogan
2. 产品卖点分条列出，每条包含"功能+好处"
3. 加入使用场景描述
4. 加入用户评价/社会证明模块
5. 加入FAQ模块（3-5个问题）""",
    },
    "ecommerce_ad": {
        "name": "电商广告文案",
        "system": "你是一个效果广告文案专家。",
        "template": """请为以下产品写3版电商广告文案（信息流广告）：

产品名称：{product_name}
核心卖点：{key_features}
促销信息：{promotion}
目标人群：{target_audience}

要求每版文案包含：
1. 广告标题（15字以内）
2. 广告正文（30-50字）
3. 行动号召按钮文案
4. 标注该版本的策略方向（如痛点驱动、利益驱动、情感驱动）""",
    },
    # ========== 邮件营销 ==========
    "email_marketing": {
        "name": "邮件营销文案",
        "system": "你是一个邮件营销专家。",
        "template": """请写一封营销邮件：

邮件目的：{email_purpose}
目标人群：{target_audience}
核心信息：{key_message}
优惠/福利：{offer}

要求：
1. 写3个邮件标题备选
2. 邮件正文简洁有力，200-400字
3. 包含清晰的CTA按钮文案
4. 加入个性化问候
5. 移动端友好（短段落）""",
    },
    # ========== 社群运营 ==========
    "community_post": {
        "name": "社群/朋友圈文案",
        "system": "你是一个社群运营专家。",
        "template": """请写一条社群/朋友圈运营文案：

发布目的：{purpose}
目标人群：{target_audience}
核心内容：{key_content}
是否需要互动：{need_interaction}

要求：
1. 文案100-200字，轻松自然
2. 如果是互动型，要设计好互动方式
3. 适当使用emoji
4. 给出发布时间建议""",
    },
    # ========== SEO ==========
    "seo_article": {
        "name": "SEO博客文章",
        "system": "你是一个SEO内容专家。",
        "template": """请写一篇SEO优化的博客文章：

目标关键词：{keywords}
文章主题：{article_topic}
目标读者：{target_audience}

要求：
1. 标题包含主关键词
2. 开头第一段自然融入关键词
3. 正文分H2/H3结构
4. 包含FAQ区块（3-5个问题）
5. 总字数1200-2000字
6. 在文末列出建议的meta description""",
    },
    # ========== 创意发散 ==========
    "brainstorm": {
        "name": "营销活动创意发散",
        "system": "你是一个创意策划专家，擅长脑暴营销活动创意。",
        "template": """请为以下需求脑暴10个营销活动创意：

活动目的：{campaign_goal}
目标人群：{target_audience}
预算范围：{budget}
时间周期：{duration}

要求每个创意包含：
1. 创意名称
2. 一句话说明
3. 核心玩法
4. 预期效果
5. 执行难度（低/中/高）""",
    },
    # ========== 用户调研 ==========
    "survey_questions": {
        "name": "用户调研问卷设计",
        "system": "你是一个用户研究专家。",
        "template": """请设计一份用户调研问卷：

调研目的：{survey_goal}
目标人群：{target_audience}
核心问题：{key_questions}
问卷长度：{length}题

要求：
1. 包含单选、多选、开放题
2. 开头要有简短的介绍语
3. 问题排列由浅入深
4. 每个问题标注题型和目的
5. 给出预计完成时间""",
    },
}


def get_template(template_key: str) -> dict:
    """获取指定模板"""
    if template_key not in PROMPT_TEMPLATES:
        return {
            "name": template_key,
            "system": "你是一个专业的AI助手。",
            "template": "{content}",
        }
    return PROMPT_TEMPLATES[template_key]


def list_templates() -> list:
    """列出所有可用模板"""
    return [
        {"key": k, "name": v["name"]}
        for k, v in PROMPT_TEMPLATES.items()
    ]
