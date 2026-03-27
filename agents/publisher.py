"""
Publisher Agent — P004
Google Blogger API v3로 포스트 자동 업로드
버그 수정: get_scheduled_time 날짜 롤오버 처리
개선: labels 중복 제거, API 에러 상세 파싱, OG 메타 주석 삽입
"""
import os, json, datetime, time, urllib.request, urllib.parse, urllib.error

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_P  = os.path.join(BASE, "output", "posts")
OUT_L  = os.path.join(BASE, "output", "logs")
TODAY  = datetime.date.today().isoformat()

BLOG_ID       = os.environ.get("BLOGGER_BLOG_ID", "")
ACCESS_TOKEN  = os.environ.get("BLOGGER_ACCESS_TOKEN", "")   # OAuth2 access token

# 포스팅 예약 시간 (KST 기준)
SCHEDULE_TIMES_KST = ["07:00", "12:00", "18:00"]


def get_scheduled_time(post_num: int) -> str:
    """포스트 번호별 예약 시간 반환 (RFC 3339 형식)
    
    버그 수정: 기존 (h - 9) % 24 방식은 날짜 롤오버를 처리하지 못함.
    예) KST 07:00 → UTC 22:00 (전날) — 기존 코드는 날짜를 오늘로 고정해버림.
    개선: datetime.timedelta로 정확한 날짜 계산
    """
    kst_time_str = SCHEDULE_TIMES_KST[(post_num - 1) % len(SCHEDULE_TIMES_KST)]
    h, m = map(int, kst_time_str.split(":"))

    # KST datetime 생성 후 UTC로 변환 (timedelta 사용으로 날짜 롤오버 자동 처리)
    kst_dt = datetime.datetime.combine(datetime.date.today(), datetime.time(h, m))
    utc_dt = kst_dt - datetime.timedelta(hours=9)

    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def inject_og_meta_comment(html_content: str, post_meta: dict) -> str:
    """HTML content 상단에 OG 메타 태그 주석 삽입 (Blogger 커스텀 헤더 활용용)"""
    og_title       = post_meta.get("og_title", post_meta.get("title", ""))
    og_description = post_meta.get("og_description", post_meta.get("meta_description", ""))
    og_slug        = post_meta.get("slug", "")
    primary_kw     = post_meta.get("primary_keyword", "")

    og_comment = f"""<!-- ===== OG / SEO META (Blogger 테마 헤더에 추가 권장) =====
<meta property="og:title" content="{og_title}" />
<meta property="og:description" content="{og_description}" />
<meta property="og:type" content="article" />
<meta name="keywords" content="{primary_kw}" />
<link rel="canonical" href="/{og_slug}" />
===== END OG META ===== -->

"""
    return og_comment + html_content


def publish_post(post_meta: dict, html_content: str) -> dict:
    """Blogger API v3로 포스트 업로드"""
    if not BLOG_ID or not ACCESS_TOKEN:
        print("  ⚠ BLOGGER_BLOG_ID / BLOGGER_ACCESS_TOKEN 없음 — 게시 건너뜀")
        return {
            "post_num": post_meta.get("post_num", 0),
            "title":    post_meta.get("title", ""),
            "status":   "skipped",
            "reason":   "BLOGGER_BLOG_ID / BLOGGER_ACCESS_TOKEN 환경변수 없음",
            "url":      "",
        }

    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"

    # 예약 시간 설정
    post_num  = post_meta.get("post_num", 1)
    scheduled = get_scheduled_time(post_num)

    # OG 메타 주석 삽입
    html_with_og = inject_og_meta_comment(html_content, post_meta)

    # labels 중복 제거 (순서 유지)
    raw_labels = post_meta.get("labels", ["AI", "인공지능"])
    labels = list(dict.fromkeys(raw_labels))

    payload = {
        "kind":    "blogger#post",
        "title":   post_meta["title"],
        "content": html_with_og,
        "labels":  labels,
        "status":  "SCHEDULED",
        "published": scheduled,
        "customMetaData": json.dumps({
            "description":  post_meta.get("meta_description", ""),
            "og_title":     post_meta.get("og_title", ""),
            "og_description": post_meta.get("og_description", ""),
            "primary_keyword": post_meta.get("primary_keyword", ""),
        })
    }

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url + "?isDraft=false",
        data=data,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 상세 에러 파싱
        try:
            error_body = e.read().decode("utf-8")
            error_json = json.loads(error_body)
            error_msg  = error_json.get("error", {}).get("message", error_body[:200])
            error_code = error_json.get("error", {}).get("code", e.code)
        except Exception:
            error_msg  = e.reason
            error_code = e.code
        raise RuntimeError(f"Blogger API 오류 [{error_code}]: {error_msg}") from e


def refresh_access_token() -> str:
    """OAuth2 refresh token으로 access token 갱신"""
    refresh_token  = os.environ.get("BLOGGER_REFRESH_TOKEN", "")
    client_id      = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret  = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    if not all([refresh_token, client_id, client_secret]):
        return ACCESS_TOKEN

    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     client_id,
        "client_secret": client_secret,
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp  = json.loads(r.read())
            token = resp.get("access_token", "")
            os.environ["BLOGGER_ACCESS_TOKEN"] = token
            return token
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
            error_json = json.loads(error_body)
            error_msg  = error_json.get("error_description", error_json.get("error", error_body[:200]))
        except Exception:
            error_msg  = e.reason
        print(f"  ⚠ Token 갱신 실패 [{e.code}]: {error_msg} — 기존 토큰 사용")
        return ACCESS_TOKEN


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run(write_data: dict = None):
    print(f"[Publisher Agent] {TODAY} 시작")

    # Access token 갱신
    token = refresh_access_token()
    if token:
        os.environ["BLOGGER_ACCESS_TOKEN"] = token
        print("  ✅ Access token 갱신")

    if write_data is None:
        log_file = os.path.join(OUT_P, f"write_log_{TODAY}.json")
        write_data = json.load(open(log_file))

    results = []
    for meta in write_data["posts"]:
        post_num  = meta.get("post_num", 1)
        html_file = os.path.join(OUT_P, meta.get("html_file", f"post_{TODAY}_{post_num}.html"))

        print(f"\n  [{post_num}/3] 업로드: {meta['title'][:50]}")
        print(f"    예약 시간: {get_scheduled_time(post_num)} (UTC)")

        if not os.path.exists(html_file):
            print(f"    ❌ HTML 파일 없음: {html_file}")
            results.append({"post_num": post_num, "status": "error", "reason": "html not found"})
            continue

        html_content = open(html_file, encoding="utf-8").read()

        try:
            resp = publish_post(meta, html_content)
            post_url = resp.get("url", "")
            post_id  = resp.get("id", "")
            sched    = resp.get("published", "")
            print(f"    ✅ 업로드 완료")
            print(f"    URL: {post_url}")
            print(f"    예약: {sched}")
            results.append({
                "post_num":  post_num,
                "title":     meta["title"],
                "status":    "published",
                "post_id":   post_id,
                "url":       post_url,
                "scheduled": sched,
                "labels":    list(dict.fromkeys(meta.get("labels", []))),
            })
        except Exception as e:
            print(f"    ❌ 업로드 실패: {e}")
            results.append({"post_num": post_num, "title": meta.get("title",""), "status": "error", "reason": str(e)})

        time.sleep(2)  # API rate limit

    # 로그 저장
    log = {"date": TODAY, "results": results, "published_at": datetime.datetime.utcnow().isoformat()}
    os.makedirs(OUT_L, exist_ok=True)
    log_path = os.path.join(OUT_L, f"publish_log_{TODAY}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    ok = len([r for r in results if r.get("status") == "published"])
    print(f"\n[Publisher Agent] 완료 — {ok}/3 게시 성공 → {log_path}")
    return log


if __name__ == "__main__":
    run()
