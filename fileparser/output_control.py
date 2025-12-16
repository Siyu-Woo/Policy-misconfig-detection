"""
提供统一的输出控制入口。

通过 set_general_output_enabled 可以在运行期间启用/禁用 fileparser 模块内的常规输出。
各模块只需执行 `from output_control import general_print as print` 即可使用受控输出。
"""

from typing import Any

_GENERAL_OUTPUT_ENABLED = True


def set_general_output_enabled(enabled: bool) -> None:
    global _GENERAL_OUTPUT_ENABLED
    _GENERAL_OUTPUT_ENABLED = enabled


def general_print(*args: Any, **kwargs: Any) -> None:
    if _GENERAL_OUTPUT_ENABLED:
        print(*args, **kwargs)
