"""
GrowthLoop 可观测性模块
基于 Harness Engineering 五层遥测架构设计
设计参考：OpenTelemetry span/event 模型 (https://opentelemetry.io/)
实现为从零编写的结构化事件记录与追踪系统

事件层级：
  user_interaction → agent_decision → tool_call → external_api_call

核心特性：
- 结构化事件记录（JSONL 格式，磁盘持久化）
- 每 Agent 的 token 用量和 API 成本追踪
- 决策回溯（记录每个 Agent 的输入/输出/耗时）
- 类型安全：元数据只允许 number/bool，字符串需显式标记

使用方式：
    obs = Observability("growth_ops")
    obs.event("funnel_analysis_started", agent="FunnelAgent", user_count=500)
    obs.end_event("funnel_analysis_completed", tokens_in=1200, tokens_out=800, cost=0.003)
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Any, Optional


# 磁盘持久化目录
_EVENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_EVENTS_DIR, exist_ok=True)


class Observability:
    """Agent 可观测性记录器"""

    def __init__(self, session_id: str = None, log_file: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.log_file = log_file or os.path.join(_EVENTS_DIR, f"events_{self.session_id}.jsonl")
        self._current_span = None
        self._spans = []
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_cost = 0.0
        self._event_count = 0

    def event(self, name: str, **metadata):
        """记录一个观测事件"""
        evt = {
            "session": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "event": name,
            "parent_span": self._current_span,
        }
        # 类型安全过滤：只保留 number/bool，字符串需要显式标记
        for k, v in metadata.items():
            if isinstance(v, (int, float, bool)):
                evt[k] = v
            elif isinstance(v, str):
                # 字符串元数据需要显式标记（代码审查检查点）
                evt[f"_{k}"] = v
            else:
                evt[k] = str(v)

        self._write_event(evt)
        self._event_count += 1
        return evt

    def start_span(self, name: str, agent: str = None):
        """开始一个追踪跨度"""
        span_id = str(uuid.uuid4())[:8]
        parent = self._current_span
        self._current_span = span_id

        self.event(
            "span_started",
            span_id=span_id,
            parent_span=parent,
            _span_name=name,
            _agent=agent or "",
        )
        return span_id

    def end_span(self, span_id: str, tokens_in: int = 0, tokens_out: int = 0, cost: float = 0.0):
        """结束一个追踪跨度"""
        self._total_tokens_in += tokens_in
        self._total_tokens_out += tokens_out
        self._total_cost += cost

        self.event(
            "span_ended",
            span_id=span_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=round(cost, 4),
        )
        self._current_span = None

    def agent_event(self, agent_name: str, action: str, **metadata):
        """便捷方法：记录 Agent 级别事件"""
        return self.event(
            f"{agent_name}.{action}",
            _agent=agent_name,
            **metadata,
        )

    def record_decision(self, agent_name: str, input_summary: str, output_summary: str, duration_ms: float):
        """记录 Agent 决策（用于回溯调试）"""
        self.event(
            "decision_recorded",
            _agent=agent_name,
            _input_summary=input_summary[:500],
            _output_summary=output_summary[:500],
            duration_ms=round(duration_ms, 1),
        )

    def get_summary(self) -> dict:
        """获取本次会话的可观测性摘要"""
        return {
            "session_id": self.session_id,
            "event_count": self._event_count,
            "total_tokens_in": self._total_tokens_in,
            "total_tokens_out": self._total_tokens_out,
            "total_cost_usd": round(self._total_cost, 4),
            "log_file": self.log_file,
        }

    def _write_event(self, evt: dict):
        """写入 JSONL 事件（磁盘持久化）"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(evt, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 观测性失败不应影响主流程

    def read_events(self) -> list:
        """读取所有事件（用于调试）"""
        events = []
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        return events

    def get_recent_events(self, n: int = 20) -> list:
        """读取最近 N 个事件（用于工程面板展示）"""
        events = self.read_events()
        return events[-n:]

    def get_events_by_agent(self) -> dict:
        """按 Agent 分组统计 token 消耗"""
        agent_stats = {}
        for evt in self.read_events():
            agent = evt.get("_agent", "unknown")
            if agent not in agent_stats:
                agent_stats[agent] = {"tokens_in": 0, "tokens_out": 0, "cost": 0.0, "event_count": 0}
            agent_stats[agent]["event_count"] += 1
            agent_stats[agent]["tokens_in"] += evt.get("tokens_in", 0)
            agent_stats[agent]["tokens_out"] += evt.get("tokens_out", 0)
            agent_stats[agent]["cost"] += evt.get("cost", 0.0)
        return agent_stats


# 全局单例
_global_obs: Optional[Observability] = None


def get_observability(session_id: str = None) -> Observability:
    """获取或创建全局可观测性实例"""
    global _global_obs
    if _global_obs is None:
        _global_obs = Observability(session_id)
    return _global_obs


def reset_observability():
    """重置全局可观测性实例（用于测试）"""
    global _global_obs
    _global_obs = None
