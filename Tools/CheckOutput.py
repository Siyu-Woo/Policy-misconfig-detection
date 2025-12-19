"""
统一的策略配置核查输出模块。

该模块提供一个简单的输出框架，可根据错误编号打印对应的信息。
默认情况下会输出 “read n policy rules, all Meet configure safety baseline”。
后续如需扩展新的错误编号，只需在 ERROR_TEMPLATES 中补充即可。
"""

from typing import Dict, Any
import sys
import os

# 预置的错误信息模版，可随时扩展
ERROR_TEMPLATES: Dict[str, Dict[str, str]] = {
    "1": {
        "fault_type": "repeat policy",
        "fault_info": "Repeat with same rule",
        "recommendation": "delete {target}"
    },
    "2": {
        "fault_type": "repeat policy",
        "fault_info": "Repeat with different rules",
        "recommendation": "combine 2 rule into {suggestion}"
    },
    "3": {
        "fault_type": "repeat rule",
        "fault_info": "rules repeat",
        "recommendation": "combine 2 rule into {suggestion}"
    },
    "4": {
        "fault_type": "allow all role",
        "fault_info": "{fault_info}",
        "recommendation": "setting role restriction"
    },
    "5": {
        "fault_type": "No rule",
        "fault_info": "not setting policy rule",
        "recommendation": "[Warning] setting role restriction"
    },
    "6": {
        "fault_type": "Scope has no restriction",
        "fault_info": "system scope should setting all",
        "recommendation": "{original_expr} and system_scope:all"
    },
    "7": {
        "fault_type": "project has no restriction",
        "fault_info": "project should setting",
        "recommendation": "{original_expr} and project_id:{project_placeholder}"
    },
    "8": {
        "fault_type": "{api} privileges to regular role",
        "fault_info": "{fault_info}",
        "recommendation": "Warning: Not set the role into regular role"
    },
    "9": {
        "fault_type": "Repeat Condition",
        "fault_info": "Delete Repeat Condition",
        "recommendation": "{rule} should be delete"
    },
    "10": {
        "fault_type": "Role or Scope Over Authorization",
        "fault_info": "{api} is not being used by the assigned Role/ in the assigned Scope",
        "recommendation": "Delete the {rule}"
    },
    "11": {
        "fault_type": "API Over Authorization",
        "fault_info": "{api} is used",
        "recommendation": "Delete the {policy}"
    }
}

DEFAULT_MESSAGE = "read n policy rules, all Meet configure safety baseline"


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
            self.output(f"[Unknown Code {error_code}] {DEFAULT_MESSAGE}")
            return

        policy_name = info.get("policy_name", "")
        fault_type = template.get("fault_type", f"Code {error_code}")

        fault_info_template = template.get("fault_info", "")
        recommendation_template = template.get("recommendation", "")

        try:
            unit_suffix = ""
            if error_code == "3" and info.get("fault_unit"):
                unit_suffix = f" {{{info['fault_unit']}}}"
            fault_info = (
                fault_info_template.format(**info) if fault_info_template else ""
            )
            fault_info += unit_suffix
            recommendation = (
                recommendation_template.format(**info) if recommendation_template else ""
            )
        except KeyError as exc:
            missing = exc.args[0]
            self.output(
                f"[Invalid Data] code={error_code} 缺少字段 '{missing}'，"
                f"fallback: {DEFAULT_MESSAGE}"
            )
            return

        policy_block = policy_name.split("\n") if policy_name else []
        formatted_policy = "\n".join(f"  {line}" for line in policy_block) if policy_block else ""

        lines = [
            f"fault type: {fault_type}",
            "fault policy rule:",
            formatted_policy if formatted_policy else "  (无)",
            f"fault info: {fault_info}",
            f"recommendation: {recommendation}",
            "-" * 40
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
