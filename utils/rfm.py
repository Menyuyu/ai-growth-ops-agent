"""
RFM用户分层模型实现
基于 pandas pd.qcut 分位数评分 (https://pandas.pydata.org/)
"""

import pandas as pd
import numpy as np


def calculate_rfm_scores(
    df: pd.DataFrame,
    recency_col: str = "recency",
    frequency_col: str = "frequency",
    monetary_col: str = "monetary",
) -> pd.DataFrame:
    """
    计算RFM分数（1-5分制）

    Args:
        df: 包含用户数据的DataFrame
        recency_col: 最近一次消费距今天数（越小越好）
        frequency_col: 消费频次（越大越好）
        monetary_col: 消费金额（越大越好）

    Returns:
        添加了R/F/M分数和综合得分的DataFrame
    """
    df = df.copy()

    # R分数：最近购买天数越短，分数越高
    df["R_score"] = pd.qcut(df[recency_col], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop")

    # F分数：购买频次越高，分数越高
    df["F_score"] = pd.qcut(df[frequency_col].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")

    # M分数：消费金额越高，分数越高
    df["M_score"] = pd.qcut(df[monetary_col].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")

    # 转换为整数
    df["R_score"] = df["R_score"].astype(int)
    df["F_score"] = df["F_score"].astype(int)
    df["M_score"] = df["M_score"].astype(int)

    # RFM综合得分
    df["rfm_score"] = df["R_score"] * 100 + df["F_score"] * 10 + df["M_score"]

    return df


def segment_users(df: pd.DataFrame) -> pd.DataFrame:
    """
    基于RFM分数对用户进行分层

    分层规则：
    - 高价值用户：R>=4, F>=4, M>=4
    - 潜力用户：R>=4, F<=3, M>=3
    - 发展用户：R>=3, F>=3, M>=3
    - 一般用户：R>=3, F<=2, M<=2
    - 流失预警：R<=2, F>=3, M>=3
    - 流失用户：R<=2, F<=2, M<=2
    """
    df = df.copy()

    conditions = [
        (df["R_score"] >= 4) & (df["F_score"] >= 4) & (df["M_score"] >= 4),
        (df["R_score"] >= 4) & (df["F_score"] <= 3) & (df["M_score"] >= 3),
        (df["R_score"] >= 3) & (df["F_score"] >= 3) & (df["M_score"] >= 3),
        (df["R_score"] >= 3) & (df["F_score"] <= 2) & (df["M_score"] <= 2),
        (df["R_score"] <= 2) & (df["F_score"] >= 3) & (df["M_score"] >= 3),
        (df["R_score"] <= 2) & (df["F_score"] <= 2) & (df["M_score"] <= 2),
    ]

    labels = [
        "高价值用户",
        "潜力用户",
        "发展用户",
        "一般用户",
        "流失预警",
        "流失用户",
    ]

    df["segment"] = np.select(conditions, labels, default="其他用户")

    return df


# 各分层的运营策略描述
SEGMENT_STRATEGIES = {
    "高价值用户": "VIP客户，提供专属优惠、优先体验新品、生日礼遇，建立长期忠诚度。建议策略：会员等级体系、专属客服、新品内测邀请。",
    "潜力用户": "近期活跃且有消费能力，需要提升购买频次。建议策略：交叉销售推荐、限时优惠刺激复购、积分奖励计划。",
    "发展用户": "中等价值用户，有提升空间。建议策略：个性化推荐、满减活动、会员权益展示。",
    "一般用户": "价值较低但仍在活跃，需要激活。建议策略：新人引导优化、低价试用产品、社交裂变活动。",
    "流失预警": "曾经高价值但近期不活跃，需要挽回。建议策略：流失预警触达、回归专属优惠、满意度调研。",
    "流失用户": "已流失用户，挽回成本较高。建议策略：大规模召回活动、产品升级通知、选择性放弃低ROI用户。",
    "其他用户": "需要进一步分析的用户群体。建议策略：补充数据、重新分层、单独制定策略。",
}
