"""
策略配置核查输出模块（精简版）。

仅保留错误码 4/5/7/8 的输出格式。
"""

from typing import Dict, Any
import sys
import os

# 预置的错误信息模版，可随时扩展
ERROR_TEMPLATES: Dict[str, Dict[str, str]] = {
    "4": {"fault_type": "allow all role"},
    "5": {"fault_type": "allow all role"},
    "7": {"fault_type": "Project has no restriction"},
    "8": {"fault_type": "admin privileges to regular role"},
}

DEFAULT_MESSAGE = "read n policy rules，all Meet configure safety baseline"


class PolicyCheckReporter:
    """
    核查输出统一入口。

    Attributes:
        output_func: 用于输出的函数，默认打印到 stdout。
    """

    def __init__(self, output_func=print) -> None:
        self.output = output_func

    def report(self, error_code: str = "", **info: Any) -> None:
        """
        根据错误编号输出信息，若未提供或未匹配到则打印默认消息。

        Args:
            error_code: 预定义的错误编号，例如 "ERR001"。
            **info:     与模版匹配的关键字参数，至少应包含 policy_name。
        """
        if not error_code:
            self.output(DEFAULT_MESSAGE)
            return

        template = ERROR_TEMPLATES.get(error_code)
        if not template:
            return

        policy_name = info.get("policy_name", "")
        fault_type = template.get("fault_type", f"Code {error_code}")

        policy_block = policy_name.split("\n") if policy_name else []
        formatted_policy = " ".join(line.strip() for line in policy_block if line.strip())
        if not formatted_policy:
            formatted_policy = "(无)"

        lines = [
            f"fault policy rule：{formatted_policy}",
            f"fault type：{fault_type}",
        ]
        self.output("\n".join(lines))


def ensure_repo_on_path() -> None:
    """
    将仓库根目录加入 sys.path，方便在其他目录调用本模块。
    在容器内调用时，可在入口脚本最开始执行该函数。
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


if __name__ == "__main__":
    ensure_repo_on_path()
    reporter = PolicyCheckReporter()
    reporter.report()  # 默认输出
