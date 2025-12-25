import re
from typing import Dict, List

from . import config
from .exec_utils import docker_exec


ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def parse_check_output(output_str: str) -> List[Dict[str, object]]:
    errors = []
    output_str = ANSI_ESCAPE.sub("", output_str)
    blocks = output_str.split("-" * 40)

    for block in blocks:
        if not block.strip():
            continue
        error_item = {
            "type": "Unknown",
            "policy": "",
            "info": "",
            "recommendation": "",
            "lines": [],
        }
        lines = block.strip().split("\n")
        current_key = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("fault type:"):
                error_item["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("fault policy rule:"):
                current_key = "policy"
            elif line.startswith("fault info:"):
                current_key = None
                error_item["info"] = line.split(":", 1)[1].strip()
            elif line.startswith("recommendation:"):
                current_key = None
                error_item["recommendation"] = line.split(":", 1)[1].strip()
            elif current_key == "policy":
                error_item["policy"] += line + "\n"
                match = re.search(r"line\s+(\d+):", line)
                if match:
                    error_item["lines"].append(int(match.group(1)))
        if error_item["type"] != "Unknown" or error_item["policy"]:
            errors.append(error_item)
    return errors


def summarize_errors(errors: List[Dict[str, object]]) -> Dict[str, object]:
    summary = {"total": len(errors), "by_type": {}}
    for err in errors:
        t = err.get("type") or "Unknown"
        summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
    return summary


def run_static_check() -> Dict[str, object]:
    outputs = []
    res1 = docker_exec(
        f"python {config.PIPELINE_SCRIPT} --show-check-report",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    outputs.append(res1.stdout)
    outputs.append(res1.stderr)

    res2 = docker_exec(
        f"python {config.STAT_CHECK_SCRIPT}",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    outputs.append(res2.stdout)
    outputs.append(res2.stderr)

    res3 = docker_exec(
        f"python {config.STAT_UNKNOWN_SCRIPT} check",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    outputs.append(res3.stdout)
    outputs.append(res3.stderr)

    combined = "\n".join([out for out in outputs if out])
    errors = parse_check_output(combined)
    return {"errors": errors, "summary": summarize_errors(errors)}


def run_dynamic_check() -> Dict[str, object]:
    res = docker_exec(
        f"python {config.DYNAMIC_CHECK_SCRIPT}",
        user="admin",
        project="admin",
        use_base_env=True,
    )
    combined = res.stdout + ("\n" + res.stderr if res.stderr else "")
    errors = parse_check_output(combined)
    return {"errors": errors, "summary": summarize_errors(errors)}
