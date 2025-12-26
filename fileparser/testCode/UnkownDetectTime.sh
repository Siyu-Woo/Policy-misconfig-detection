#!/usr/bin/env bash
set -u

RESULT_DIR="/root/policy-fileparser/testCode/test_results"
RESULT_FILE="${RESULT_DIR}/performance_unknown_single.csv"
RUNS=10

mkdir -p "$RESULT_DIR"

# 更新 CSV 表头，与逻辑保持一致
echo "run_id,start_time,end_time,duration_ms,duration_sec" > "$RESULT_FILE"

# 定义数组存储耗时
declare -a durations

for i in $(seq 1 $RUNS); do
  echo "--------------------------------------------------"
  echo "Run $i/$RUNS"
  
  # 记录开始时间
  start_human=$(date '+%Y-%m-%d %H:%M:%S')
  t1=$(date +%s%3N)
  echo "开始时间: $start_human"
  echo "开始时间戳(t1): $t1"

  # 执行 Python 脚本 (保留了原有的参数)
  python /root/policy-fileparser/testCode/AuthorizationScopeCheck.py \
    --policy /etc/openstack/policies/TestPolicyFiles/policyB.yaml \
    --parsed-logs /root/policy-fileparser/data/assistfile/rbac_audit_keystone.csv \
    --output console
  status=$?

  # 记录结束时间
  t2=$(date +%s%3N)
  end_human=$(date '+%Y-%m-%d %H:%M:%S')
  
  echo "结束时间: $end_human"
  echo "结束时间戳(t2): $t2"

  if [ $status -eq 0 ]; then
    echo "✓ 检测程序执行完成"
  else
    echo "✗ 检测程序执行失败"
    exit 1
  fi

  # 计算耗时
  single_duration_ms=$((t2 - t1))
  
  # 使用 awk 计算秒数，保留小数点后两位 (%.2f)
  single_duration_sec=$(awk "BEGIN {printf \"%.2f\", $single_duration_ms / 1000}")

  # 终端打印本次结果
  echo ">> 本次耗时: ${single_duration_sec} 秒"

  # 写入文件
  echo "$i,$start_human,$end_human,$single_duration_ms,$single_duration_sec" >> "$RESULT_FILE"

  # 存入数组
  durations+=("$single_duration_sec")
  
  echo ""
done

echo "=================================================="
echo "执行完成，以下是 ${RUNS} 次运行的详细耗时统计："

# 遍历数组输出最后结果
count=1
for d in "${durations[@]}"; do
  echo "第 $count 次: $d 秒"
  ((count++))
done