"""
熔断器模块（Circuit Breaker）
基于 Harness Engineering 的"防 runaway loop"原则设计
设计参考：Netflix Hystrix Circuit Breaker pattern (https://github.com/Netflix/Hystrix)
实现为从零编写的 3 状态机（CLOSED → OPEN → HALF_OPEN）

原理：当 Agent 的某个操作连续失败 N 次后，自动进入"降级模式"，
不再重复尝试，而是降级到更安全的策略（如人工审核、使用默认值）。

三级状态机：
  CLOSED（正常） → OPEN（熔断） → HALF_OPEN（试探恢复）

状态转换：
  CLOSED → OPEN：连续 failure_threshold 次失败
  OPEN → HALF_OPEN：冷却期后尝试一次
  HALF_OPEN → CLOSED：成功 → 恢复
  HALF_OPEN → OPEN：再次失败 → 重置冷却期

使用方式：
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
    result = cb.execute(lambda: risky_operation(), fallback=default_value)
"""

import time
from typing import Callable, Any, Optional


class CircuitBreaker:
    """熔断器：防 Agent 无限重试同一失败操作"""

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 300,
        name: str = "default",
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._total_failures = 0
        self._total_successes = 0
        self._last_error = None

    @property
    def state(self) -> str:
        """获取当前状态（自动处理冷却期）"""
        if self._state == self.STATE_OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.cooldown_seconds:
                self._state = self.STATE_HALF_OPEN
        return self._state

    def execute(self, func: Callable, fallback: Any = None, **kwargs) -> Any:
        """
        在熔断器保护下执行函数

        Args:
            func: 要执行的函数
            fallback: 熔断时返回的降级值
            **kwargs: 传递给 func 的参数

        Returns:
            func 的返回值，或 fallback（熔断时）
        """
        current_state = self.state

        if current_state == self.STATE_OPEN:
            # 熔断中，直接返回降级值
            return fallback

        try:
            result = func(**kwargs) if callable(func) else func
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            return fallback

    def record_success(self):
        """手动记录成功"""
        self._on_success()

    def record_failure(self, error: Exception = None):
        """手动记录失败"""
        self._on_failure(error)

    def _on_success(self):
        """成功处理"""
        self._success_count += 1
        self._total_successes += 1
        if self._state == self.STATE_HALF_OPEN:
            self._state = self.STATE_CLOSED
            self._failure_count = 0

    def _on_failure(self, error: Exception = None):
        """失败处理"""
        self._failure_count += 1
        self._total_failures += 1
        self._last_error = error
        self._last_failure_time = time.time()

        if self._state == self.STATE_HALF_OPEN:
            # 试探恢复失败，重新熔断（冷却期翻倍）
            self.cooldown_seconds *= 2
            self._state = self.STATE_OPEN
        elif self._failure_count >= self.failure_threshold:
            self._state = self.STATE_OPEN

    def reset(self):
        """重置熔断器"""
        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._last_error = None

    def get_status(self) -> dict:
        """获取熔断器状态"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": round(self.cooldown_seconds, 0),
            "last_error": str(self._last_error) if self._last_error else None,
        }


class AgentCircuitBreakers:
    """管理多个 Agent 的熔断器"""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 300):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, agent_name: str) -> CircuitBreaker:
        """获取或创建指定 Agent 的熔断器"""
        if agent_name not in self._breakers:
            self._breakers[agent_name] = CircuitBreaker(
                failure_threshold=self.failure_threshold,
                cooldown_seconds=self.cooldown_seconds,
                name=agent_name,
            )
        return self._breakers[agent_name]

    def get_all_status(self) -> list:
        """获取所有熔断器状态"""
        return [cb.get_status() for cb in self._breakers.values()]

    def reset_all(self):
        """重置所有熔断器"""
        for cb in self._breakers.values():
            cb.reset()
