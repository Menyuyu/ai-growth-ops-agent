"""
增长记忆Agent
记录历史增长实验效果，让系统越用越聪明
"""

import json
import os
from datetime import datetime


class GrowthMemory:
    """增长知识库 - 持久化存储增长实验经验"""

    def __init__(self, filepath: str = "data/growth_memory.json"):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        """加载历史数据"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "segment_strategies": {},  # segment -> {strategy -> {wins, losses, best_content}}
            "funnel_improvements": [],  # 漏斗改善记录
            "template_rankings": {},  # template -> {segment -> [scores]}
            "cycle_summaries": [],  # 增长周期总结
        }

    def _save(self):
        """保存数据"""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def record_cycle_result(
        self,
        segment: str,
        strategy: str,
        ab_result: dict,
        template_used: str,
    ):
        """记录一次增长周期结果"""
        # 记录分层策略效果
        if segment not in self.data["segment_strategies"]:
            self.data["segment_strategies"][segment] = {}
        if strategy not in self.data["segment_strategies"][segment]:
            self.data["segment_strategies"][segment][strategy] = {
                "wins": 0,
                "losses": 0,
                "best_content": "",
                "total_uplift": 0,
            }

        # 清理 numpy 类型，转为原生 Python 类型
        clean_result = {}
        for k, v in ab_result.items():
            if hasattr(v, "item"):
                clean_result[k] = v.item()
            elif isinstance(v, bool):
                clean_result[k] = bool(v)
            elif isinstance(v, (int, float)):
                clean_result[k] = float(v)
            else:
                clean_result[k] = v

        entry = self.data["segment_strategies"][segment][strategy]
        if clean_result.get("significant", False):
            entry["wins"] += 1
            entry["best_content"] = clean_result.get("winning_variant", "")
        else:
            entry["losses"] += 1

        uplift = clean_result.get("lift_percent", 0)
        entry["total_uplift"] += float(uplift)

        # 记录模板效果
        if template_used not in self.data["template_rankings"]:
            self.data["template_rankings"][template_used] = {}
        if segment not in self.data["template_rankings"][template_used]:
            self.data["template_rankings"][template_used][segment] = []
        self.data["template_rankings"][template_used][segment].append(float(uplift))

        # 记录漏斗改善
        self.data["funnel_improvements"].append({
            "timestamp": datetime.now().isoformat(),
            "segment": segment,
            "strategy": strategy,
            "uplift": float(uplift),
            "significant": bool(clean_result.get("significant", False)),
        })

        self._save()

    def get_best_strategy(self, segment: str) -> str:
        """获取某分层最有效的策略"""
        if segment not in self.data["segment_strategies"]:
            return ""
        strategies = self.data["segment_strategies"][segment]
        best = max(strategies.items(), key=lambda x: x[1]["wins"] - x[1]["losses"])
        return best[0] if best[1]["wins"] > best[1]["losses"] else ""

    def get_template_score(self, template: str, segment: str) -> float:
        """获取模板在某分层的效果评分"""
        if template in self.data["template_rankings"]:
            scores = self.data["template_rankings"][template].get(segment, [])
            return sum(scores) / len(scores) if scores else 0
        return 0

    def get_cycle_summary(self) -> list:
        """获取增长周期总结"""
        return self.data["cycle_summaries"]

    def add_cycle_summary(self, summary: dict):
        """添加周期总结"""
        self.data["cycle_summaries"].append({
            "timestamp": datetime.now().isoformat(),
            **summary,
        })
        self._save()

    def get_knowledge_report(self) -> str:
        """生成知识库报告"""
        lines = ["## 增长知识库报告", ""]
        lines.append("### 各分层最有效策略")
        for segment, strategies in self.data["segment_strategies"].items():
            if strategies:
                best = max(strategies.items(), key=lambda x: x[1]["wins"])
                lines.append(f"- **{segment}**: {best[0]} (胜{best[1]['wins']}次)")
        lines.append("")
        lines.append("### 漏斗改善记录")
        for record in self.data["funnel_improvements"][-5:]:
            sig = "✅" if record["significant"] else "❌"
            lines.append(f"- {record['segment']}: {record['strategy']} → {record['uplift']:+.1f}% {sig}")
        return "\n".join(lines)
