from http.server import BaseHTTPRequestHandler
from datetime import datetime
import json
import os
import requests

# Upstash Redis配置（从环境变量读取）
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

def redis_command(cmd, *args):
    """执行Redis命令"""
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    
    url = f"{REDIS_URL}/{cmd}"
    for arg in args:
        url += f"/{arg}"
    
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        return response.json()
    except:
        return None

def redis_incr(key):
    """递增Redis键"""
    if not REDIS_URL or not REDIS_TOKEN:
        return 0
    
    url = f"{REDIS_URL}/INCR/{key}"
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()
        return result.get("result", 0) if isinstance(result, dict) else 0
    except:
        return 0

def redis_sadd(key, value):
    """向Set添加元素"""
    if not REDIS_URL or not REDIS_TOKEN:
        return 0
    
    url = f"{REDIS_URL}/SADD/{key}/{value}"
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()
        return result.get("result", 0) if isinstance(result, dict) else 0
    except:
        return 0

def redis_scard(key):
    """获取Set的大小"""
    if not REDIS_URL or not REDIS_TOKEN:
        return 0
    
    url = f"{REDIS_URL}/SCARD/{key}"
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()
        return result.get("result", 0) if isinstance(result, dict) else 0
    except:
        return 0

def redis_get(key):
    """获取Redis键值"""
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    
    url = f"{REDIS_URL}/GET/{key}"
    headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()
        return result.get("result") if isinstance(result, dict) else None
    except:
        return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """处理统计数据上报"""
        try:
            # 读取请求数据
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
            data = json.loads(post_data.decode('utf-8'))
            
            skill_name = data.get("skill_name", "unknown")
            user_id = data.get("user_id", "unknown")
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 更新统计数据
            total_calls = redis_incr("stats:total_calls")
            skill_calls = redis_incr(f"stats:skill:{skill_name}:total")
            daily_calls = redis_incr(f"stats:daily:{today}:total")
            daily_skill_calls = redis_incr(f"stats:daily:{today}:skill:{skill_name}")
            
            # 记录用户（去重）
            redis_sadd("stats:users", user_id)
            redis_sadd(f"stats:daily:{today}:users", user_id)
            
            # 返回成功
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "total_calls": total_calls,
                "skill_calls": skill_calls
            }).encode('utf-8'))
            
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))
    
    def do_GET(self):
        """获取统计数据"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            total_calls = redis_get("stats:total_calls") or 0
            total_users = redis_scard("stats:users")
            daily_calls = redis_get(f"stats:daily:{today}:total") or 0
            daily_users = redis_scard(f"stats:daily:{today}:users")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "total_calls": int(total_calls) if str(total_calls).isdigit() else 0,
                "total_users": total_users,
                "today": {
                    "date": today,
                    "calls": int(daily_calls) if str(daily_calls).isdigit() else 0,
                    "users": daily_users
                }
            }, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode('utf-8'))
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
