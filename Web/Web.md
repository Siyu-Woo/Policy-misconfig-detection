# Web UI Guide

## Architecture
- Browser UI: `Web/templates/index.html` (markup), `Web/static/css/style.css` (theme), `Web/static/js/main.js` (state + UI logic).
- External UI libs: Vis Network for graph rendering, Prism for code highlighting (loaded via CDN in `Web/templates/index.html`).
- API server: Flask in `Web/app.py` serving HTML + JSON endpoints.
- Backend ops layer: `Web/Backbone/` modules orchestrate Docker exec/cp, parsing, checks, and Neo4j queries.
- State and files on host:
  - `Web/TempFile/policy` and `Web/TempFile/log` store exported/imported files.
  - `Web/TempFile/state.json` caches current selections and parse/check results.

## Frontend-to-Backend Mapping
- App boot + polling:
  - `refreshState()` -> `GET /api/state` -> `STATE` + file lists.
  - `setInterval()` -> `GET /api/status` -> `container_ops.get_container_status()`.
- Context and terminal:
  - `loadContextOptions()` -> `GET /api/context/options` -> `openstack_ops.collect_env_options()`.
  - `handleContextChange()` -> `POST /api/context` -> `container_ops.switch_context()` -> `CurrentUserSet.sh`.
  - `sendTerminalCommand()` -> `POST /api/terminal` -> `container_ops.exec_terminal_command()`.
  - `container-restart` -> `POST /api/container/restart` -> `container_ops.restart_container()`.
- File export/import:
  - Export policy -> `POST /api/export/policy` -> `policy_ops.export_policy()` (runs `Policyset.py export`).
  - Export log -> `POST /api/export/log` -> `log_ops.export_log()` (docker cp from container).
  - Import policy -> `POST /api/import/policy` -> `policy_ops.import_policy_file()`.
  - Import log -> `POST /api/import/log` -> `log_ops.import_log_file()`.
  - Apply policy (run view) -> `POST /api/apply/policy` -> `policy_ops.apply_policy_to_container()` + `restart_container()` + `restart_keystone()`.
- File view:
  - Select file -> `POST /api/files/select` -> updates `STATE`, resets parse/check caches.
  - Load content -> `GET /api/file/content` -> reads from `Web/TempFile`.
- Parsing and graph:
  - Parse policy -> `POST /api/policy/parse` -> `policy_ops.ensure_policy_in_container()` + `run_policy_pipeline()` + `parse_policy_file()` + `graph_ops.get_graph_stats()`.
  - Graph data -> `GET /api/graph` -> `graph_ops.get_graph_data()` (Neo4j).
  - Parse log -> `POST /api/log/parse` -> `log_ops.ensure_log_in_container()` + `log_ops.parse_rbac_log()`.
- Checks:
  - Static check -> `POST /api/check/static` -> `check_ops.run_static_check()`.
  - Dynamic check -> `POST /api/check/dynamic` -> `check_ops.run_dynamic_check()`.
- Environment overview:
  - `GET /api/env/overview` -> `openstack_ops.collect_env_overview()`.

## Interaction Logic
- Startup sequence:
  1) `refreshState()` loads cached selections and file lists.
  2) `loadContextOptions(true)` fetches users/domains.
  3) Default mode is Run (`setMode('run')`), Manage tabs are initialized but hidden.
  4) A 15s poll updates Docker status and context pill.
- Run mode:
  - Terminal commands go to the container with the current user/project/domain context.
  - User/domain selection refreshes options and updates the active context via `CurrentUserSet.sh`.
  - Export/import actions write to `Web/TempFile` and refresh cached state.
- Manage mode:
  - File page shows the currently selected file; content is cached and highlighted by Prism.
  - Policy page uses one-time parsing per file; graph loads on demand.
  - Log page parses once per file (unless re-imported).
  - Checks page runs only on button click; results are cached until files change.
- Focus/highlight:
  - Clicking a policy row or graph node sets focus to API and highlights both views.
  - Search boxes change focus type (api/role/project) and update highlights.
  - Clicking a check card pins focus with a color; clicking again clears focus.

## Key Files
- `Web/templates/index.html`: layout and DOM ids used by the JS controller.
- `Web/static/js/main.js`: state machine, API calls, event binding.
- `Web/app.py`: Flask routes and request flow.
- `Web/Backbone/exec_utils.py`: sudo + docker exec/cp helpers.
- `Web/Backbone/*_ops.py`: container, policy, log, checks, graph, and OpenStack data.
