import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import config


DEFAULT_STATE = {
    "context": {
        "user": "admin",
        "project": "admin",
        "domain": "",
        "scope": "",
        "auth_url": "",
        "region": "",
    },
    "current_policy_file": None,
    "current_log_file": None,
    "policy_parse": {
        "ready": False,
        "file": None,
        "excel": [],
        "stats": {},
        "summary": {},
    },
    "log_parse": {
        "ready": False,
        "file": None,
        "rows": [],
        "summary": {},
    },
    "checks": {
        "static": {"ready": False, "errors": [], "summary": {}},
        "dynamic": {"ready": False, "errors": [], "summary": {}},
    },
    "env_options": {
        "ready": False,
        "users": [],
        "projects": [],
        "domains": [],
    },
}


@dataclass
class StateStore:
    data: Dict[str, Any] = field(default_factory=dict)

    def load(self) -> None:
        if config.STATE_FILE.exists():
            try:
                self.data = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
                for key, value in DEFAULT_STATE.items():
                    if key not in self.data:
                        self.data[key] = json.loads(json.dumps(value))
                return
            except (json.JSONDecodeError, OSError):
                pass
        self.data = json.loads(json.dumps(DEFAULT_STATE))

    def save(self) -> None:
        config.STATE_FILE.write_text(json.dumps(self.data, ensure_ascii=True, indent=2), encoding="utf-8")

    def reset_policy_parse(self) -> None:
        self.data["policy_parse"] = json.loads(json.dumps(DEFAULT_STATE["policy_parse"]))

    def reset_log_parse(self) -> None:
        self.data["log_parse"] = json.loads(json.dumps(DEFAULT_STATE["log_parse"]))

    def reset_checks(self) -> None:
        self.data["checks"] = json.loads(json.dumps(DEFAULT_STATE["checks"]))

    def set_env_options(self, users: list, projects: list, domains: list) -> None:
        self.data["env_options"] = {
            "ready": True,
            "users": users,
            "projects": projects,
            "domains": domains,
        }

    def reset_env_options(self) -> None:
        self.data["env_options"] = json.loads(json.dumps(DEFAULT_STATE["env_options"]))

    def update_context(self, context: Dict[str, str]) -> None:
        self.data["context"].update(context)

    def set_current_file(self, file_type: str, filename: Optional[str]) -> None:
        key = "current_policy_file" if file_type == "policy" else "current_log_file"
        self.data[key] = filename

    def set_policy_parse(self, filename: str, excel: list, stats: dict, summary: dict) -> None:
        self.data["policy_parse"] = {
            "ready": True,
            "file": filename,
            "excel": excel,
            "stats": stats,
            "summary": summary,
        }

    def set_log_parse(self, filename: str, rows: list, summary: dict) -> None:
        self.data["log_parse"] = {
            "ready": True,
            "file": filename,
            "rows": rows,
            "summary": summary,
        }

    def set_check_result(self, check_type: str, errors: list, summary: dict) -> None:
        self.data["checks"][check_type] = {
            "ready": True,
            "errors": errors,
            "summary": summary,
        }

    def get(self, key: str, default=None):
        return self.data.get(key, default)


STATE = StateStore()
STATE.load()
