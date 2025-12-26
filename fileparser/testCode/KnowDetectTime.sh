#!/usr/bin/env bash
set -u

RESULT_DIR="/root/policy-fileparser/testCode/test_results"
RESULT_FILE="${RESULT_DIR}/performance_single.csv"
RUNS=10

mkdir -p "$RESULT_DIR"

# 更新 CSV 表头，增加 Run ID
echo "run_id,start_time,end_time,duration_ms,duration_sec" > "$RESULT_FILE"

# 定义一个数组用来存储每次的耗时
declare -a durations

for i in $(seq 1 $RUNS); do
  echo "--------------------------------------------------"
  echo "Run $i/$RUNS"
  
  # 获取开始时间
  start_human=$(date '+%Y-%m-%d %H:%M:%S')
  t1=$(date +%s%3N)
  
  echo "开始时间: $start_human"
  echo "开始时间戳(t1): $t1"

  # 执行 Python 脚本
  python /root/policy-fileparser/testCode/PolicyDoctor.py --output console
  status=$?

  # 获取结束时间
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

  # 打印本次耗时
  echo ">> 本次耗时: ${single_duration_sec} 秒"

  # 写入 CSV (记录更详细的数据以备后用)
  echo "$i,$start_human,$end_human,$single_duration_ms,$single_duration_sec" >> "$RESULT_FILE"
  
  # 将本次耗时存入数组
  durations+=("$single_duration_sec")
  
  echo ""
done

echo "=================================================="
echo "执行完成，以下是 ${RUNS} 次运行的详细耗时统计："

# 遍历数组并输出
count=1
for d in "${durations[@]}"; do
  echo "第 $count 次: $d 秒"
  ((count++))
done