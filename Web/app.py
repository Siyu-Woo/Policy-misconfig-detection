import os
import shutil
import subprocess
import re
import yaml
import json
import sys
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- 配置路径 ---
UPLOAD_FOLDER = '/etc/openstack/policies'
# 根据 Manual.md 和用户提供的路径
PROJECT_ROOT = '/root' 
CHECK_SCRIPT = '/root/StatisticDetect/StatisticCheck.py'
PIPELINE_SCRIPT = '/root/policy-fileparser/run_graph_pipeline.py'

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def run_command(command, cwd, env):
    """
    封装的命令执行函数：
    1. 执行命令
    2. 将输出打印到容器终端 (便于调试)
    3. 返回输出给前端
    """
    print(f"\n{'='*20} START EXECUTING {'='*20}")
    print(f"Command: {' '.join(command)}")
    print(f"CWD: {cwd}")
    
    try:
        # capture_output=True 会吞掉终端输出，所以我们需要手动 print
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env,
            cwd=cwd
        )
        
        # --- 关键：将捕获的内容打印到容器终端 ---
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
    """解析 CheckOutput.py 格式的输出"""
    errors = []
    # 移除 ANSI 颜色代码（如果有）
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
        
        # 只有当解析出有效类型时才添加，避免添加空块
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
        
        # 准备环境：继承当前 shell 环境变量 (包括 OpenStack 认证信息)
        env = os.environ.copy()
        # 关键：添加 PYTHONPATH 为 /root，这样 policy-fileparser 能引用 Tools
        env['PYTHONPATH'] = f"/root:{env.get('PYTHONPATH', '')}"
        
        try:
            # 运行 pipeline 解析脚本
            result = run_command(
                ['python3', PIPELINE_SCRIPT],
                cwd='/root/policy-fileparser', # 设置正确的 CWD
                env=env
            )
            
            if result.returncode != 0:
                # 如果脚本报错，返回 stderr 给前端
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
    """运行检查并返回结构化数据"""
    env = os.environ.copy()
    env['PYTHONPATH'] = f"/root:{env.get('PYTHONPATH', '')}"
    
    all_outputs = ""
    
    print("\n>>> STARTING SECURITY CHECK SEQUENCE <<<")

    # 1. 运行 Pipeline Check (Duplicates)
    # 这里的 show-check-report 参数会让脚本输出 CheckOutput 格式的日志
    res1 = run_command(
        ['python3', PIPELINE_SCRIPT, '--show-check-report'],
        cwd='/root/policy-fileparser',
        env=env
    )
    all_outputs += res1.stdout
    if res1.stderr:
        print(f"Pipeline Stderr: {res1.stderr}")

    # 2. 运行 Statistic Check (Graph Analysis)
    res2 = run_command(
        ['python3', CHECK_SCRIPT],
        cwd='/root/StatisticDetect',
        env=env
    )
    all_outputs += res2.stdout
    if res2.stderr:
        print(f"Statistic Stderr: {res2.stderr}")

    print(">>> CHECK SEQUENCE FINISHED. PARSING OUTPUT... <<<")

    # 3. 解析
    parsed_errors = parse_check_output(all_outputs)
    print(f"Parsed {len(parsed_errors)} errors.")
    
    # 统计信息
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
        'raw_log': all_outputs # 方便前端调试查看原始日志
    })

if __name__ == '__main__':
    # 确保监听 80 端口，debug=True 方便在终端看到请求日志
    app.run(host='0.0.0.0', port=80, debug=True)