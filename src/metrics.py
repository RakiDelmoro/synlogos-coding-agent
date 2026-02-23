"""Tool usage metrics and logging for Synlogos"""
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime


@dataclass
class ToolUsageMetrics:
    """Track tool usage statistics"""
    tool_name: str
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_execution_time_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 0.0
        return (self.success_count / self.call_count) * 100


@dataclass
class SessionMetrics:
    """Track metrics for an entire session"""
    session_start: datetime = field(default_factory=datetime.now)
    total_prompts: int = 0
    direct_tool_calls: int = 0
    orchestration_calls: int = 0
    tool_usage: Dict[str, ToolUsageMetrics] = field(default_factory=dict)
    
    def record_tool_call(self, tool_name: str, success: bool, execution_time_ms: float = 0.0):
        """Record a tool call"""
        if tool_name not in self.tool_usage:
            self.tool_usage[tool_name] = ToolUsageMetrics(tool_name=tool_name)
        
        metrics = self.tool_usage[tool_name]
        metrics.call_count += 1
        metrics.total_execution_time_ms += execution_time_ms
        
        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
        
        # Track direct vs orchestration
        if tool_name == "orchestrate":
            self.orchestration_calls += 1
        else:
            self.direct_tool_calls += 1
    
    def record_prompt(self):
        """Record a user prompt"""
        self.total_prompts += 1
    
    def get_summary(self) -> str:
        """Get a formatted summary of metrics"""
        lines = [
            "=" * 60,
            "SESSION METRICS",
            "=" * 60,
            f"Session duration: {datetime.now() - self.session_start}",
            f"Total prompts: {self.total_prompts}",
            f"Direct tool calls: {self.direct_tool_calls}",
            f"Orchestration calls: {self.orchestration_calls}",
            "",
            "Tool Usage Breakdown:",
            "-" * 60,
        ]
        
        for tool_name, metrics in sorted(self.tool_usage.items(), key=lambda x: x[1].call_count, reverse=True):
            lines.append(f"  {tool_name:20} {metrics.call_count:3} calls  {metrics.success_rate:5.1f}% success")
        
        lines.extend([
            "-" * 60,
            f"Hybrid ratio: {self.direct_tool_calls}:{self.orchestration_calls} (direct:orchestrate)",
            "=" * 60,
        ])
        
        return "\n".join(lines)


# Global metrics instance
_session_metrics: SessionMetrics = SessionMetrics()


def get_session_metrics() -> SessionMetrics:
    """Get the current session metrics"""
    return _session_metrics


def reset_session_metrics():
    """Reset session metrics (call at start of new session)"""
    global _session_metrics
    _session_metrics = SessionMetrics()


def record_tool_execution(tool_name: str, success: bool, execution_time_ms: float = 0.0):
    """Record a tool execution"""
    _session_metrics.record_tool_call(tool_name, success, execution_time_ms)


def record_user_prompt():
    """Record a user prompt"""
    _session_metrics.record_prompt()


def print_session_summary():
    """Print session summary to console"""
    print(_session_metrics.get_summary())
