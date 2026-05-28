---
name: weaver-ecology
description: 泛微OA E9 接口集成 — 查流程、批待办、搜人员
metadata:
  openclaw:
    emoji: 🏢
    requires:
      bins: [curl, python3, openssl]
---

# 泛微 OA Ecology E9 — OpenClaw Skill

纯 Python CLI 工具，通过 OA 原生 REST API 操作泛微 E9。**不含 MCP、不含外部依赖**。

## 环境变量

| 变量 | 说明 |
|------|------|
| `WEAVER_BASE_URL` | OA 地址，如 `http://192.168.1.100` |
| `WEAVER_APP_ID` | 许可证号 |
| `WEAVER_RSA_PRIVATE_KEY` | RSA 私钥 PEM（不填自动生成） |
| `WEAVER_RSA_PUBLIC_KEY` | RSA 公钥 PEM（不填自动生成） |

## 接口认证流程

1. `POST /api/ec/dev/auth/regist` — 发 APPID + 公钥，拿 secrit + spk
2. `POST /api/ec/dev/auth/applytoken` — 用 spk 加密 secrit，拿 token
3. 后续请求头带 `token` + `appid` + 加密的 `userid`

## AI 使用方式

### 查流程列表
```bash
python3 scripts/weaver.py workflow-list --user-id 1
```

### 发起流程
```bash
python3 scripts/weaver.py workflow-create \
  --user-id 1 --workflow-id "123" --title "请假申请"
```

### 查流程进度
```bash
python3 scripts/weaver.py workflow-query \
  --user-id 1 --request-id "456"
```

### 审批
```bash
python3 scripts/weaver.py workflow-approve \
  --user-id 1 --request-id "456" --approve --opinion "同意"
```

### 查人员
```bash
python3 scripts/weaver.py user-query \
  --user-id 1 --by loginid --value "zhangsan"
```

### 查部门
```bash
python3 scripts/weaver.py dept-query --user-id 1
```

### 通用接口
```bash
python3 scripts/weaver.py api-call \
  --path "/api/hrm/employee/search" --method POST \
  --params '{"keyword":"张三"}'
```

## AI 使用示例

```
用户：查一下我的待办流程
→ AI 执行 weaver.py workflow-list --user-id 1
→ 返回 JSON → "你有 3 条待办：
   1. 【请假申请】部门经理审批中
   2. 【费用报销】财务审核中
   3. 【合同审批】法务会签中"
```

## OA 侧配置

1. 接口白名单（`ecology/WEB-INF/prop/weaver_session_filter.properties`）：
   ```
   unchecksessionurl=/api/ec/dev/auth/regist;/api/ec/dev/auth/applytoken;
   ```

2. 数据库：
   ```sql
   INSERT INTO ECOLOGY_BIZ_EC(ID, APPID, NAME)
   VALUES('123456', '你的APPID', 'MCP服务');
   ```
