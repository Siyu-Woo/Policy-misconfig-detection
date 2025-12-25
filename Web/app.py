import os

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from Backbone import config
from Backbone.check_ops import run_dynamic_check, run_static_check
from Backbone.container_ops import exec_terminal_command, get_container_status, restart_container, switch_context
from Backbone.graph_ops import get_graph_data, get_graph_stats
from Backbone.log_ops import choose_default_log_file, ensure_log_in_container, export_log, import_log_file, list_log_files, parse_rbac_log
from Backbone.openstack_ops import collect_env_options, collect_env_overview
from Backbone.policy_ops import (
    apply_policy_to_container,
    choose_default_policy_file,
    ensure_policy_in_container,
    export_policy,
    import_policy_file,
    list_policy_files,
    parse_policy_file,
    restart_keystone,
    run_policy_pipeline,
)
from Backbone.state import STATE

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def _ensure_current_files() -> None:
    policy_file = STATE.get("current_policy_file")
    if not policy_file or not (config.TEMP_POLICY_DIR / policy_file).exists():
        policy_file = choose_default_policy_file()
        STATE.set_current_file("policy", policy_file)
        STATE.reset_policy_parse()

    log_file = STATE.get("current_log_file")
    if not log_file or not (config.TEMP_LOG_DIR / log_file).exists():
        log_file = choose_default_log_file()
        STATE.set_current_file("log", log_file)
        STATE.reset_log_parse()

    STATE.save()


def _normalize_filename(filename: str, default_ext: str) -> str:
    cleaned = secure_filename(filename)
    if not cleaned:
        cleaned = f"upload{default_ext}"
    if not cleaned.lower().endswith(default_ext):
        cleaned = f"{cleaned}{default_ext}"
    return cleaned


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    _ensure_current_files()
    return jsonify(
        {
            "container": get_container_status(),
            "context": STATE.get("context"),
            "files": {
                "policy": list_policy_files(),
                "log": list_log_files(),
            },
            "current": {
                "policy": STATE.get("current_policy_file"),
                "log": STATE.get("current_log_file"),
            },
            "policy_parse": STATE.get("policy_parse"),
            "log_parse": STATE.get("log_parse"),
            "checks": STATE.get("checks"),
            "env_options": STATE.get("env_options"),
        }
    )


@app.route("/api/status")
def api_status():
    return jsonify({"container": get_container_status(), "context": STATE.get("context")})


@app.route("/api/context", methods=["POST"])
def api_context():
    payload = request.get_json(silent=True) or {}
    user = payload.get("user")
    project = payload.get("project")
    domain = payload.get("domain")
    context = switch_context(user=user, project=project, domain=domain)
    return jsonify(context)


@app.route("/api/context/options")
def api_context_options():
    refresh = request.args.get("refresh") == "1"
    cached = STATE.get("env_options", {})
    if cached.get("ready") and not refresh:
        return jsonify(cached)
    options = collect_env_options()
    STATE.set_env_options(
        users=options.get("users", []),
        projects=options.get("projects", []),
        domains=options.get("domains", []),
    )
    STATE.save()
    return jsonify(STATE.get("env_options"))


@app.route("/api/terminal", methods=["POST"])
def api_terminal():
    payload = request.get_json(silent=True) or {}
    command = (payload.get("command") or "").strip()
    if not command:
        return jsonify({"error": "empty command"}), 400
    result = exec_terminal_command(command)
    return jsonify(result)


@app.route("/api/container/restart", methods=["POST"])
def api_container_restart():
    result = restart_container()
    return jsonify(result)


@app.route("/api/export/policy", methods=["POST"])
def api_export_policy():
    result = export_policy()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/export/log", methods=["POST"])
def api_export_log():
    result = export_log()
    return jsonify(result)


@app.route("/api/import/policy", methods=["POST"])
def api_import_policy():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    file = request.files["file"]
    filename = _normalize_filename(file.filename or "policy.yaml", ".yaml")
    content = file.read()
    stored = import_policy_file(filename, content)
    return jsonify({"file": stored})


@app.route("/api/import/log", methods=["POST"])
def api_import_log():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    file = request.files["file"]
    filename = _normalize_filename(file.filename or "keystone.log", ".log")
    content = file.read()
    stored = import_log_file(filename, content)
    return jsonify({"file": stored})


@app.route("/api/apply/policy", methods=["POST"])
def api_apply_policy():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    file = request.files["file"]
    filename = _normalize_filename(file.filename or "policy.yaml", ".yaml")
    content = file.read()
    stored = import_policy_file(filename, content)

    restart_log = restart_container()
    path = config.TEMP_POLICY_DIR / stored
    result = apply_policy_to_container(str(path))
    keystone = restart_keystone()
    return jsonify({"file": stored, "restart": restart_log, "apply": result, "keystone": keystone})


@app.route("/api/files/select", methods=["POST"])
def api_select_file():
    payload = request.get_json(silent=True) or {}
    file_type = payload.get("type")
    filename = payload.get("filename")
    if file_type not in ("policy", "log"):
        return jsonify({"error": "invalid type"}), 400
    STATE.set_current_file(file_type, filename)
    if file_type == "policy":
        STATE.reset_policy_parse()
    else:
        STATE.reset_log_parse()
    STATE.reset_checks()
    STATE.save()
    return jsonify({"ok": True})


@app.route("/api/file/content")
def api_file_content():
    file_type = request.args.get("type")
    filename = request.args.get("filename")
    if file_type not in ("policy", "log"):
        return jsonify({"error": "invalid type"}), 400
    if not filename:
        return jsonify({"error": "missing filename"}), 400
    directory = config.TEMP_POLICY_DIR if file_type == "policy" else config.TEMP_LOG_DIR
    path = directory / filename
    if not path.exists():
        return jsonify({"error": "file not found"}), 404
    content = path.read_text(encoding="utf-8", errors="ignore")
    return jsonify({"filename": filename, "content": content})


@app.route("/api/policy/parse", methods=["POST"])
def api_parse_policy():
    _ensure_current_files()
    filename = STATE.get("current_policy_file")
    if not filename:
        return jsonify({"error": "no policy file"}), 400
    payload = request.get_json(silent=True) or {}
    force = payload.get("force", False)
    cached = STATE.get("policy_parse", {})
    if cached.get("ready") and cached.get("file") == filename and not force:
        return jsonify(cached)

    path = config.TEMP_POLICY_DIR / filename

    ensure_policy_in_container(path)
    pipeline_log = run_policy_pipeline()
    excel = parse_policy_file(path)
    stats = {}
    try:
        stats = get_graph_stats()
    except Exception:
        stats = {}

    summary = {"lines": len(excel)}
    STATE.set_policy_parse(filename, excel, stats, summary)
    STATE.save()
    payload = dict(STATE.get("policy_parse") or {})
    payload["log"] = pipeline_log
    return jsonify(payload)


@app.route("/api/log/parse", methods=["POST"])
def api_parse_log():
    _ensure_current_files()
    filename = STATE.get("current_log_file")
    if not filename:
        return jsonify({"error": "no log file"}), 400
    payload = request.get_json(silent=True) or {}
    force = payload.get("force", False)
    cached = STATE.get("log_parse", {})
    if cached.get("ready") and cached.get("file") == filename and not force:
        return jsonify(cached)

    path = config.TEMP_LOG_DIR / filename

    ensure_log_in_container(path)
    parsed = parse_rbac_log()
    rows = parsed.get("rows", [])

    summary = {"rows": len(rows)}
    STATE.set_log_parse(filename, rows, summary)
    STATE.save()
    return jsonify(STATE.get("log_parse"))


@app.route("/api/graph")
def api_graph():
    try:
        data = get_graph_data()
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/check/static", methods=["POST"])
def api_check_static():
    policy_state = STATE.get("policy_parse", {})
    current_policy = STATE.get("current_policy_file")
    if not policy_state.get("ready") or policy_state.get("file") != current_policy:
        return jsonify({"error": "policy not parsed"}), 400
    payload = request.get_json(silent=True) or {}
    force = payload.get("force", False)
    cached = STATE.get("checks", {}).get("static", {})
    if cached.get("ready") and not force:
        return jsonify(cached)

    result = run_static_check()
    STATE.set_check_result("static", result["errors"], result["summary"])
    STATE.save()
    return jsonify(result)


@app.route("/api/check/dynamic", methods=["POST"])
def api_check_dynamic():
    policy_state = STATE.get("policy_parse", {})
    log_state = STATE.get("log_parse", {})
    current_policy = STATE.get("current_policy_file")
    current_log = STATE.get("current_log_file")
    if not policy_state.get("ready") or policy_state.get("file") != current_policy:
        return jsonify({"error": "policy not parsed"}), 400
    if not log_state.get("ready") or log_state.get("file") != current_log:
        return jsonify({"error": "log not parsed"}), 400
    payload = request.get_json(silent=True) or {}
    force = payload.get("force", False)
    cached = STATE.get("checks", {}).get("dynamic", {})
    if cached.get("ready") and not force:
        return jsonify(cached)

    result = run_dynamic_check()
    STATE.set_check_result("dynamic", result["errors"], result["summary"])
    STATE.save()
    return jsonify(result)


@app.route("/api/env/overview")
def api_env_overview():
    overview = collect_env_overview()
    return jsonify(overview)


if __name__ == "__main__":
    port = int(os.environ.get("WEB_PORT", "20175"))
    app.run(host="0.0.0.0", port=port, debug=True)
