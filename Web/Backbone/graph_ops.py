from typing import Dict, List, Tuple

from neo4j import GraphDatabase


NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Password"

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def get_graph_data(limit: int = 400) -> Dict[str, List[Dict[str, object]]]:
    drv = get_driver()
    nodes = []
    edges = []
    node_ids = set()

    def serialize_node(node) -> Dict[str, object]:
        labels = list(node.labels) if node.labels else []
        label = labels[0] if labels else "Node"
        color = "#a3bffa"
        if "PolicyNode" in labels:
            color = "#fbb6ce"
        elif "RuleNode" in labels:
            color = "#9ae6b4"
        elif "ConditionNode" in labels:
            color = "#faf089"
        label_prop = node.get("name") or node.get("expression") or str(node.id)
        return {
            "id": node.id,
            "label": label_prop,
            "group": label,
            "color": color,
            "title": str(dict(node)),
            "labels": labels,
            "cond_type": node.get("type", ""),
        }

    query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT $limit"
    with drv.session() as session:
        result = session.run(query, limit=limit)
        for record in result:
            n, r, m = record["n"], record["r"], record["m"]
            if n.id not in node_ids:
                nodes.append(serialize_node(n))
                node_ids.add(n.id)
            if m.id not in node_ids:
                nodes.append(serialize_node(m))
                node_ids.add(m.id)
            edges.append({"from": n.id, "to": m.id, "label": type(r).__name__, "arrows": "to"})
    return {"nodes": nodes, "edges": edges}


def get_graph_stats() -> Dict[str, int]:
    drv = get_driver()
    stats = {
        "api": 0,
        "rule": 0,
        "role": 0,
        "project": 0,
        "user": 0,
    }
    with drv.session() as session:
        stats["api"] = session.run("MATCH (n:PolicyNode) RETURN count(n) as c").single()["c"]
        stats["rule"] = session.run("MATCH (n:RuleNode) RETURN count(n) as c").single()["c"]
        stats["user"] = session.run("MATCH (n:User) RETURN count(n) as c").single()["c"]

        role_count = session.run(
            "MATCH (n:ConditionNode {type: 'role'}) RETURN count(DISTINCT n.name) as c"
        ).single()["c"]
        proj_count = session.run(
            "MATCH (n:ConditionNode) WHERE n.type IN ['project', 'project_id'] RETURN count(DISTINCT n.name) as c"
        ).single()["c"]
        stats["role"] = role_count
        stats["project"] = proj_count
    return stats
