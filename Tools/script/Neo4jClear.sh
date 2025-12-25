#!/usr/bin/env bash
set -u

python - <<'PY'
from openstackpolicygraph import PolicyGraphCreator

g = PolicyGraphCreator("bolt://localhost:7687", "neo4j", "Password")
g.clear_database()
g.close()
PY
