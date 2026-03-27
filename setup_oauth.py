"""
Google OAuth2 초기 설정 스크립트
최초 1회 실행 → refresh_token 발급 → .env에 저장
"""
import os, sys, json, urllib.request, urllib.parse, webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env_path = os.path.join(BASE, ".env")
    if os.path.exists(env_path):
        for line in open(env_path).read().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip()

load_env()

CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI  = "urn:ietf:wg:oauth:2.0:oob"

SCOPES = [
    "https://www.googleapis.com/auth/blogger",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def get_auth_url():
    params = {
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


def exchange_code(code: str) -> dict:
    data = urllib.parse.urlencode({
        "code":          code,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def save_tokens(tokens: dict):
    env_path = os.path.join(BASE, ".env")
    content  = open(env_path).read() if os.path.exists(env_path) else ""

    for key, env_var in [
        (tokens.get("access_token",""),  "BLOGGER_ACCESS_TOKEN"),
        (tokens.get("refresh_token",""), "BLOGGER_REFRESH_TOKEN"),
    ]:
        if not key:
            continue
        if f"{env_var}=" in content:
            lines = content.splitlines()
            content = "\n".join(
                f"{env_var}={key}" if l.startswith(f"{env_var}=") else l
                for l in lines
            )
        else:
            content += f"\n{env_var}={key}"

    with open(env_path, "w") as f:
        f.write(content)
    print(f"  .env 저장 완료")


if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ .env에 GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET 설정 필요")
        sys.exit(1)

    auth_url = get_auth_url()
    print(f"\n1. 아래 URL을 브라우저에서 열어 Google 계정으로 로그인하세요:")
    print(f"\n   {auth_url}\n")

    try:
        webbrowser.open(auth_url)
        print("   (브라우저 자동으로 열림)")
    except:
        pass

    code = input("\n2. 인증 후 받은 코드를 입력하세요: ").strip()

    print("\n3. 토큰 교환 중...")
    tokens = exchange_code(code)
    print(f"   access_token: {tokens.get('access_token','')[:20]}...")
    print(f"   refresh_token: {tokens.get('refresh_token','')[:20]}...")

    save_tokens(tokens)
    print("\n✅ OAuth2 설정 완료! 이제 run_daily.py를 실행할 수 있습니다.")
