#!/usr/bin/env python3
"""
泛微 OA E9 CLI 工具 — 纯 Python，零外部依赖

用法：
  export WEAVER_BASE_URL=http://192.168.1.100
  export WEAVER_APP_ID=xxx

  python3 weaver.py workflow-list --user-id 1
  python3 weaver.py workflow-query --user-id 1 --request-id "456"
  python3 weaver.py workflow-approve --user-id 1 --request-id "456" --approve --opinion "同意"
  python3 weaver.py workflow-create --user-id 1 --workflow-id "123" --title "请假申请"
  python3 weaver.py user-query --user-id 1 --by loginid --value "zhangsan"
  python3 weaver.py dept-query --user-id 1
  python3 weaver.py api-call --path "/api/hrm/employee/search" --method POST --params '{"keyword":"张三"}'
"""

import os, sys, json, base64, subprocess, tempfile, argparse
from urllib.request import Request, urlopen
from urllib.parse import urlencode

# ── RSA 工具（基于 openssl CLI） ──

def generate_key_pair():
    """生成 RSA 2048 密钥对"""
    tmpdir = tempfile.mkdtemp()
    priv_path = os.path.join(tmpdir, "priv.pem")
    pub_path = os.path.join(tmpdir, "pub.pem")
    subprocess.run(
        ["openssl", "genrsa", "-out", priv_path, "2048"],
        capture_output=True, check=True
    )
    subprocess.run(
        ["openssl", "rsa", "-in", priv_path, "-pubout", "-out", pub_path],
        capture_output=True, check=True
    )
    with open(priv_path) as f: priv = f.read()
    with open(pub_path) as f: pub = f.read()
    # cleanup
    for p in [priv_path, pub_path]: os.remove(p)
    os.rmdir(tmpdir)
    return priv, pub

def rsa_encrypt_base64(plain_text: str, pub_key_pem: str) -> str:
    """用公钥 RSA-OAEP 加密，输出 base64"""
    tmpdir = tempfile.mkdtemp()
    pub_path = os.path.join(tmpdir, "pub.pem")
    input_path = os.path.join(tmpdir, "input.bin")
    output_path = os.path.join(tmpdir, "output.bin")
    
    with open(pub_path, "w") as f: f.write(pub_key_pem)
    with open(input_path, "w") as f: f.write(plain_text)
    
    subprocess.run([
        "openssl", "pkeyutl", "-encrypt",
        "-inkey", pub_path, "-pubin",
        "-in", input_path, "-out", output_path,
        "-pkeyopt", "rsa_padding_mode:oaep",
        "-pkeyopt", "rsa_oaep_md:sha256",
        "-pkeyopt", "rsa_mgf1_md:sha256",
    ], capture_output=True, check=True)
    
    with open(output_path, "rb") as f: encrypted = f.read()
    
    for p in [pub_path, input_path, output_path]: os.remove(p)
    os.rmdir(tmpdir)
    
    return base64.b64encode(encrypted).decode()

# ── OA HTTP 客户端 ──

class WeaverClient:
    def __init__(self):
        self.base_url = os.environ.get("WEAVER_BASE_URL", "").rstrip("/")
        self.app_id = os.environ.get("WEAVER_APP_ID", "")
        if not self.base_url or not self.app_id:
            print("❌ 请设置环境变量 WEAVER_BASE_URL 和 WEAVER_APP_ID", file=sys.stderr)
            sys.exit(1)
        
        self.priv_key = os.environ.get("WEAVER_RSA_PRIVATE_KEY", "")
        self.pub_key = os.environ.get("WEAVER_RSA_PUBLIC_KEY", "")
        
        if not self.priv_key or not self.pub_key:
            self.priv_key, self.pub_key = generate_key_pair()
        
        self._token = None
        self._spk = None
    
    def _req(self, url, headers=None, data=None, method="POST"):
        req = Request(url, method=method, data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            resp = urlopen(req, timeout=30)
            body = resp.read().decode("utf-8")
            return json.loads(body)
        except Exception as e:
            print(f"❌ 请求失败: {e}", file=sys.stderr)
            sys.exit(1)
    
    def _register(self):
        """注册许可证"""
        url = f"{self.base_url}/api/ec/dev/auth/regist"
        data = urlencode({"appid": self.app_id, "cpk": self.pub_key}).encode()
        result = self._req(url, data=data)
        if not result.get("status"):
            print(f"❌ 注册失败: {result.get('errmsg', result.get('msg', '未知错误'))}", file=sys.stderr)
            sys.exit(1)
        return result["secrit"], result["spk"]
    
    def _apply_token(self, secrit, spk):
        """用 spk 加密 secrit 换取 token"""
        url = f"{self.base_url}/api/ec/dev/auth/applytoken"
        secret = rsa_encrypt_base64(secrit, spk)
        data = urlencode({"appid": self.app_id, "secret": secret}).encode()
        result = self._req(url, data=data)
        if not result.get("status"):
            print(f"❌ 获取 Token 失败: {result.get('errmsg', result.get('msg', '未知错误'))}", file=sys.stderr)
            sys.exit(1)
        return result["token"]
    
    def _ensure_token(self):
        if self._token:
            return self._token
        secrit, spk = self._register()
        self._spk = spk
        self._token = self._apply_token(secrit, spk)
        return self._token
    
    def _encrypt_userid(self, user_id):
        if not self._spk:
            self._ensure_token()
        return rsa_encrypt_base64(str(user_id), self._spk)
    
    def call_api(self, path, params=None, user_id=None, method="POST"):
        """调用 OA 业务接口"""
        token = self._ensure_token()
        url = f"{self.base_url}{path}"
        
        headers = {"token": token, "appid": self.app_id}
        if user_id is not None:
            headers["userid"] = self._encrypt_userid(user_id)
        
        data = None
        if params and method != "GET":
            data = urlencode(params).encode()
        
        return self._req(url, headers=headers, data=data, method=method)
    
    def call_whitelist_api(self, path, params=None, method="POST"):
        """调用白名单接口（无需 userid）"""
        token = self._ensure_token()
        url = f"{self.base_url}{path}"
        headers = {"token": token, "appid": self.app_id, "skipsession": "1"}
        data = None
        if params and method != "GET":
            data = urlencode(params).encode()
        return self._req(url, headers=headers, data=data, method=method)

# ── CLI 入口 ──

def main():
    parser = argparse.ArgumentParser(description="泛微 OA E9 CLI 工具")
    sub = parser.add_subparsers(dest="command")
    
    # workflow-list
    p = sub.add_parser("workflow-list", help="查询流程模板列表")
    p.add_argument("--user-id", type=int, required=True)
    
    # workflow-query
    p = sub.add_parser("workflow-query", help="查询流程进度")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--request-id", required=True)
    
    # workflow-approve
    p = sub.add_parser("workflow-approve", help="审批流程")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--request-id", required=True)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--opinion", default="同意")
    p.add_argument("--next-node-id")
    
    # workflow-create
    p = sub.add_parser("workflow-create", help="发起流程")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--workflow-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--fields", help='JSON 格式的字段值，如 {"原因":"生病"}')
    p.add_argument("--tables", help='JSON 格式的明细表数据')
    
    # user-query
    p = sub.add_parser("user-query", help="查人员信息")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--by", choices=["id", "loginid", "lastname"], default="loginid")
    p.add_argument("--value", required=True)
    
    # dept-query
    p = sub.add_parser("dept-query", help="查部门信息")
    p.add_argument("--user-id", type=int, required=True)
    p.add_argument("--dept-id")
    
    # api-call
    p = sub.add_parser("api-call", help="通用接口调用")
    p.add_argument("--path", required=True)
    p.add_argument("--method", default="POST", choices=["GET", "POST", "PUT", "DELETE"])
    p.add_argument("--user-id", type=int)
    p.add_argument("--params", help='JSON 格式参数')
    p.add_argument("--whitelist", action="store_true", help="是否白名单接口")
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    client = WeaverClient()
    
    if args.command == "workflow-list":
        result = client.call_api("/api/workflow/list", method="GET", user_id=args.user_id)
    
    elif args.command == "workflow-query":
        result = client.call_api("/api/workflow/request/status",
                                 params={"requestId": args.request_id},
                                 user_id=args.user_id)
    
    elif args.command == "workflow-approve":
        params = {
            "requestId": args.request_id,
            "approve": "1" if args.approve else "0",
            "opinion": args.opinion,
        }
        if args.next_node_id:
            params["nextNodeId"] = args.next_node_id
        result = client.call_api("/api/workflow/request/approve",
                                 params=params, user_id=args.user_id)
    
    elif args.command == "workflow-create":
        params = {"workflowId": args.workflow_id, "requestName": args.title}
        if args.fields:
            params["detailFields"] = args.fields
        if args.tables:
            params["detailTables"] = args.tables
        result = client.call_api("/api/workflow/request/create",
                                 params=params, user_id=args.user_id)
    
    elif args.command == "user-query":
        result = client.call_api(
            f"/api/hrm/employee/{args.by}/{args.value}",
            method="GET", user_id=args.user_id)
    
    elif args.command == "dept-query":
        path = f"/api/hrm/department/get/{args.dept_id}" if args.dept_id else "/api/hrm/department/list"
        result = client.call_api(path, method="GET", user_id=args.user_id)
    
    elif args.command == "api-call":
        params = json.loads(args.params) if args.params else None
        if args.whitelist:
            result = client.call_whitelist_api(args.path, params=params, method=args.method)
        else:
            result = client.call_api(args.path, params=params, user_id=args.user_id, method=args.method)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
