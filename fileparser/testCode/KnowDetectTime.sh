#!/usr/bin/env bash
set -u

RESULT_DIR="/root/policy-fileparser/testCode/test_results"
RESULT_FILE="${RESULT_DIR}/performance_single.csv"
RUNS=10

mkdir -p "$RESULT_DIR"

echo "timestamp_ms,start_time,end_time,duration_ms,duration_sec" > "$RESULT_FILE"

total_ms=0

for i in $(seq 1 $RUNS); do
  echo "Run $i/$RUNS"
  start_time=$(date '+%Y-%m-%d %H:%M:%S')
  t1=$(date +%s%3N)
  echo "开始时间: $start_time"
  echo "开始时间戳(t1): $t1 毫秒"

  python /root/policy-fileparser/testCode/PolicyDoctor.py --output console
  status=$?

  if [ $status -eq 0 ]; then
    echo "✓ 检测程序执行完成"
  else
    echo "✗ 检测程序执行失败"
    exit 1
  fi

  end_time=$(date '+%Y-%m-%d %H:%M:%S')
  t2=$(date +%s%3N)
  echo "结束时间: $end_time"
  echo "结束时间戳(t2): $t2 毫秒"

  single_duration=$((t2 - t1))
  total_ms=$((total_ms + single_duration))
  single_duration_sec=$(awk "BEGIN {printf \"%.3f\", $single_duration / 1000}")

  echo "$(date '+%Y-%m-%d %H:%M:%S'),$start_time,$end_time,$single_duration,$single_duration_sec" >> "$RESULT_FILE"
  echo ""
done

avg_ms=$((total_ms / RUNS))
avg_sec=$(awk "BEGIN {printf \"%.3f\", $avg_ms / 1000}")

echo "平均耗时: ${avg_ms} ms (${avg_sec} s)"
