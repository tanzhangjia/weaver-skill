#!/usr/bin/env bash
# 快速验证泛微 OA 连接

set -e

PYTHON_CMD="python3"

print_usage() {
    cat <<EOF
用法: ./quick-test.sh [user-id]

快速测试泛微 OA 连接：
1. 自动注册并获取 token
2. 查询流程列表
3. 查询部门列表

参数:
  user-id    OA 用户 ID (默认: 1)

环境变量:
  WEAVER_BASE_URL    OA 地址
  WEAVER_APP_ID      许可证号

示例:
  WEAVER_BASE_URL=http://192.168.1.100 WEAVER_APP_ID=xxx ./quick-test.sh 1
EOF
}

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    print_usage
    exit 0
fi

USER_ID="${1:-1}"

echo "🔍 测试泛微 OA 连接..."
echo "   用户 ID: $USER_ID"

echo ""
echo "--- 流程列表 ---"
$PYTHON_CMD scripts/weaver.py workflow-list --user-id "$USER_ID" 2>/dev/null && echo "✅ 成功" || echo "❌ 失败"

echo ""
echo "--- 部门列表 ---"
$PYTHON_CMD scripts/weaver.py dept-query --user-id "$USER_ID" 2>/dev/null && echo "✅ 成功" || echo "❌ 失败"

echo ""
echo "--- 用户信息 ---"
$PYTHON_CMD scripts/weaver.py user-query --user-id "$USER_ID" --by id --value "$USER_ID" 2>/dev/null && echo "✅ 成功" || echo "❌ 失败"
