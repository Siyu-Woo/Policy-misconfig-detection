#!/usr/bin/env bash
set -u

python - <<'PY'
import sys

sys.path.insert(0, "/root/policy-fileparser")
from openstackpolicygraph import PolicyGraphCreator

g = PolicyGraphCreator("bolt://localhost:7687", "neo4j", "Password")
g.clear_database()
g.close()
PY
