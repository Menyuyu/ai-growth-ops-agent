"""
生成SaaS用户模拟数据
覆盖完整用户生命周期行为，用于增长运营系统演示
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

n_users = 500
today = datetime(2026, 4, 9)

# 用户ID
user_ids = [f"U{i:04d}" for i in range(1, n_users + 1)]

# 注册日期（过去90天内）
signup_dates = [today - timedelta(days=int(d)) for d in np.random.uniform(1, 90, n_users)]

# 渠道
channels = np.random.choice(
    ["自然搜索", "付费广告", "社交媒体", "直接访问", "推荐"],
    size=n_users, p=[0.3, 0.25, 0.2, 0.15, 0.1]
)

# 用户类型
plan_types = np.random.choice(
    ["试用版", "免费版", "专业版", "企业版"],
    size=n_users, p=[0.4, 0.3, 0.2, 0.1]
)

# 漏斗阶段（模拟流失）
# 注册 -> 浏览 -> 首次使用 -> 活跃 -> 付费
def generate_funnel_stage(plan):
    if plan == "试用版":
        stages = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
        # 试用版流失严重
        probs = [0.15, 0.25, 0.30, 0.20, 0.10]
    elif plan == "免费版":
        stages = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
        probs = [0.10, 0.15, 0.25, 0.30, 0.20]
    else:
        stages = ["已注册", "已浏览", "首次使用", "已活跃", "已付费"]
        probs = [0.05, 0.05, 0.10, 0.30, 0.50]
    return np.random.choice(stages, p=probs)

funnel_stages = [generate_funnel_stage(p) for p in plan_types]

# 设计数量（基于漏斗阶段）
def generate_design_count(stage, plan):
    stage_order = {"已注册": 0, "已浏览": 1, "首次使用": 2, "已活跃": 3, "已付费": 4}
    level = stage_order.get(stage, 0)
    if level == 0:
        return 0
    elif level == 1:
        return np.random.randint(0, 2)
    elif level == 2:
        return np.random.randint(1, 8)
    elif level == 3:
        return np.random.randint(3, 30)
    else:
        return np.random.randint(10, 100)

design_counts = [generate_design_count(s, p) for s, p in zip(funnel_stages, plan_types)]

# 导出数量（约为设计数的30%）
export_counts = [int(d * np.random.uniform(0.1, 0.5)) for d in design_counts]

# 分享数量（约为设计数的10%）
share_counts = [int(d * np.random.uniform(0.02, 0.2)) for d in design_counts]

# 会话数
session_counts = [max(1, int(d * np.random.uniform(0.5, 1.5))) for d in design_counts]

# 平均会话时长（分钟）
session_durations = [round(np.random.uniform(2, 45), 1) if sc > 0 else 0 for sc in session_counts]

# 功能使用数
features_used = [min(15, max(1, int(dc * np.random.uniform(0.5, 2.0)))) for dc in design_counts]

# 最近活跃天数
def generate_recency(stage):
    stage_order = {"已注册": 0, "已浏览": 1, "首次使用": 2, "已活跃": 3, "已付费": 4}
    level = stage_order.get(stage, 0)
    if level <= 1:
        return np.random.randint(30, 90)
    elif level == 2:
        return np.random.randint(7, 45)
    else:
        return np.random.randint(0, 14)

recency = [generate_recency(s) for s in funnel_stages]

# 总消费金额（仅付费用户）
monetary = []
for plan, stage in zip(plan_types, funnel_stages):
    if stage == "已付费":
        if plan == "专业版":
            monetary.append(round(np.random.uniform(99, 999), 2))
        else:
            monetary.append(round(np.random.uniform(499, 4999), 2))
    else:
        monetary.append(0.0)

# 试用剩余天数
trial_days = [max(0, int(14 - (today - sd).days)) if p == "试用版" else 0 for p, sd in zip(plan_types, signup_dates)]

# 注册天数
days_since_signup = [(today - sd).days for sd in signup_dates]

# 是否完成核心动作（创建第一个设计）
has_completed_core = [dc > 0 for dc in design_counts]

# 是否打开过上次的营销邮件
email_opened = np.random.choice([True, False], size=n_users, p=[0.35, 0.65])

# 流失风险评分（综合计算）
def calculate_churn_risk(recency, stage, plan):
    stage_order = {"已注册": 4, "已浏览": 3, "首次使用": 2, "已活跃": 1, "已付费": 0}
    score = stage_order.get(stage, 3) * 20
    score += min(recency, 60)
    if plan == "试用版":
        score += 10
    return min(100, score)

churn_risks = [calculate_churn_risk(r, s, p) for r, s, p in zip(recency, funnel_stages, plan_types)]

# 构建DataFrame
df = pd.DataFrame({
    "user_id": user_ids,
    "signup_date": [d.strftime("%Y-%m-%d") for d in signup_dates],
    "channel": channels,
    "plan_type": plan_types,
    "funnel_stage": funnel_stages,
    "recency_days": recency,
    "frequency_sessions": session_counts,
    "monetary_spent": monetary,
    "design_count": design_counts,
    "export_count": export_counts,
    "share_count": share_counts,
    "avg_session_duration": session_durations,
    "features_used": features_used,
    "trial_days_remaining": trial_days,
    "days_since_signup": days_since_signup,
    "has_completed_core_action": has_completed_core,
    "email_opened_last_campaign": email_opened,
    "churn_risk_score": churn_risks,
})

# 保存
df.to_csv("data/mock_users_saas.csv", index=False, encoding="utf-8-sig")
print(f"已生成 {len(df)} 条SaaS用户数据 -> data/mock_users_saas.csv")
print(f"\n漏斗分布：")
print(df["funnel_stage"].value_counts())
print(f"\n用户类型分布：")
print(df["plan_type"].value_counts())
print(f"\n字段：{list(df.columns)}")
