import os
import shutil
import subprocess
import re
import yaml
import json
import sys
import traceback
from flask import Flask, render_template, request, jsonify
from neo4j import GraphDatabase

app = Flask(__name__)

# --- 配置路径 ---
UPLOAD_FOLDER = '/etc/openstack/policies'
PROJECT_ROOT = '/root' 
CHECK_SCRIPT = '/root/StatisticDetect/StatisticCheck.py'
PIPELINE_SCRIPT = '/root/policy-fileparser/run_graph_pipeline.py'

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= Neo4j 配置 =================
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
# 注意：如果你之前在终端里把密码改成了 '123456'，请这里改成 '123456'
# 如果没改过，保持 'Password'
NEO4J_PASSWORD = "Password"  

# 全局驱动变量 (懒加载)
driver = None

def get_driver():
    """获取 Neo4j 驱动实例 (单例模式)"""
    global driver
    if driver is None:
        try:
            print(f"Connecting to Neo4j at {NEO4J_URI} as {NEO4J_USER}...")
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # 测试连接
            driver.verify_connectivity()
            print("Neo4j Connected Successfully!")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            driver = None
    return driver
# ============================================

def run_command(command, cwd, env):
    print(f"\n{'='*20} START EXECUTING {'='*20}")
    print(f"Command: {' '.join(command)}")
    print(f"CWD: {cwd}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
            cwd=cwd
        )
        
        if result.stdout:
            print(f"--- STDOUT ---\n{result.stdout}")
        if result.stderr:
            print(f"--- STDERR ---\n{result.stderr}")
        
        if result.returncode != 0:
            print(f"!!! EXECUTION FAILED (Return Code: {result.returncode}) !!!")
        else:
            print("--- EXECUTION SUCCESS ---")
        print(f"{'='*20} END EXECUTING {'='*20}\n")
            
        return result
    except Exception as e:
        print(f"!!! EXCEPTION: {str(e)}")
        raise e

def parse_check_output(output_str):
    errors = []
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    output_str = ansi_escape.sub('', output_str)

    blocks = output_str.split('-' * 40)
    
    for block in blocks:
        if not block.strip():
            continue
            
        error_item = {
            'type': 'Unknown',
            'policy': '',
            'info': '',
            'recommendation': '',
            'lines': [] 
        }
        
        lines = block.strip().split('\n')
        current_key = None
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith('fault type:'):
                error_item['type'] = line.split(':', 1)[1].strip()
            elif line.startswith('fault policy rule:'):
                current_key = 'policy'
            elif line.startswith('fault info:'):
                current_key = None
                error_item['info'] = line.split(':', 1)[1].strip()
            elif line.startswith('recommendation:'):
                current_key = None
                error_item['recommendation'] = line.split(':', 1)[1].strip()
            elif current_key == 'policy':
                error_item['policy'] += line + "\n"
                match = re.search(r'line\s+(\d+):', line)
                if match:
                    error_item['lines'].append(int(match.group(1)))
        
        if error_item['type'] != 'Unknown' or error_item['policy']:
            errors.append(error_item)
            
    return errors

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = "policy.yaml" 
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        try:
            file.save(filepath)
            print(f"File saved to: {filepath}")
        except Exception as e:
            print(f"Failed to save file: {e}")
            return jsonify({'success': False, 'error': f"File save failed: {str(e)}"}), 500
        
        env = os.environ.copy()
        env['PYTHONPATH'] = f"/root:{env.get('PYTHONPATH', '')}"
        
        try:
            result = run_command(
                ['python3', PIPELINE_SCRIPT],
                cwd='/root/policy-fileparser', 
                env=env
            )
            
            if result.returncode != 0:
                return jsonify({
                    'success': False, 
                    'error': f"Script Error: {result.stderr}",
                    'log': result.stdout
                }), 500
            
            return jsonify({
                'success': True,
                'log': result.stdout,
                'error_log': result.stderr
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_file_content')
def get_file_content():
    filepath = os.path.join(UPLOAD_FOLDER, 'policy.yaml')
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    excel_data = []
    
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if ':' in line_clean and not line_clean.startswith('#'):
            parts = line_clean.split(':', 1)
            if len(parts) >= 2:
                name = parts[0].strip().strip('"').strip("'")
                rule = parts[1].strip().strip('"').strip("'")
                excel_data.append({
                    'line': idx + 1,
                    'name': name,
                    'rule': rule
                })
            
    return jsonify({
        'raw_content': content,
        'excel_data': excel_data
    })

@app.route('/run_check')
def run_check():
    env = os.environ.copy()
    env['PYTHONPATH'] = f"/root:{env.get('PYTHONPATH', '')}"
    
    all_outputs = ""
    print("\n>>> STARTING SECURITY CHECK SEQUENCE <<<")

    res1 = run_command(
        ['python3', PIPELINE_SCRIPT, '--show-check-report'],
        cwd='/root/policy-fileparser',
        env=env
    )
    all_outputs += res1.stdout
    if res1.stderr:
        print(f"Pipeline Stderr: {res1.stderr}")

    res2 = run_command(
        ['python3', CHECK_SCRIPT],
        cwd='/root/StatisticDetect',
        env=env
    )
    all_outputs += res2.stdout
    if res2.stderr:
        print(f"Statistic Stderr: {res2.stderr}")

    print(">>> CHECK SEQUENCE FINISHED. PARSING OUTPUT... <<<")

    parsed_errors = parse_check_output(all_outputs)
    
    summary = {
        'total': len(parsed_errors),
        'by_type': {}
    }
    for err in parsed_errors:
        t = err['type']
        summary['by_type'][t] = summary['by_type'].get(t, 0) + 1
        
    return jsonify({
        'errors': parsed_errors,
        'summary': summary,
        'raw_log': all_outputs
    })

@app.route('/get_graph_data')
def get_graph_data():
    """
    后端直接连接 Neo4j，获取数据并转换为 Vis.js 格式
    """
    try:
        # 获取驱动（如果失败则返回 None）
        drv = get_driver()
        if not drv:
            return jsonify({"error": "Neo4j driver initialization failed. Check server logs for details."}), 500

        query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 300"
        
        nodes = []
        edges = []
        node_ids = set()

        def serialize_node(node):
            label = list(node.labels)[0] if node.labels else "Node"
            color = "#97c2fc"
            if "PolicyNode" in node.labels: color = "#ffcccc"
            elif "RuleNode" in node.labels: color = "#ccffcc"
            elif "ConditionNode" in node.labels: color = "#ffffcc"
            
            label_prop = node.get("name") or node.get("expression") or str(node.id)
            
            return {
                "id": node.id,
                "label": label_prop,
                "group": label,
                "color": color,
                "title": str(dict(node))
            }

        with drv.session() as session:
            result = session.run(query)
            for record in result:
                n, r, m = record["n"], record["r"], record["m"]
                
                if n.id not in node_ids:
                    nodes.append(serialize_node(n))
                    node_ids.add(n.id)
                
                if m.id not in node_ids:
                    nodes.append(serialize_node(m))
                    node_ids.add(m.id)
                
                edges.append({
                    "from": n.id,
                    "to": m.id,
                    "label": type(r).__name__,
                    "arrows": "to"
                })
                
        return jsonify({"nodes": nodes, "edges": edges})

    except Exception as e:
        # 关键：打印详细错误堆栈到终端，方便调试
        print("!!! GRAPH DATA ERROR !!!")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 监听 0.0.0.0:80
    app.run(host='0.0.0.0', port=80, debug=True)