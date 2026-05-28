# 🏢 weaver-skill

OpenClaw Skill — 泛微 OA Ecology E9 接口集成。

**纯 Python CLI 工具，零外部依赖，零 MCP。**

## 文件结构

```
weaver-skill/
├── SKILL.md              # skill 定义
├── README.md
└── scripts/
    ├── weaver.py         # CLI 主程序（Python 3，仅标准库 + openssl）
    └── quick-test.sh     # 快速连接测试
```

## 使用

```bash
export WEAVER_BASE_URL=http://192.168.1.100
export WEAVER_APP_ID=your-app-id

# 查流程
python3 scripts/weaver.py workflow-list --user-id 1

# 审批
python3 scripts/weaver.py workflow-approve \
  --user-id 1 --request-id "456" --approve --opinion "同意"
```

## License

Apache-2.0
