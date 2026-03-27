"""
P004 — 메인 실행 스크립트
매일 자동 실행: Research → SEO → Writer → SEO검증 → Publisher
개선: Step 3.5 SEO 자동 검증 추가
"""
import os, sys, json, datetime, time, traceback, re

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# .env 로드
def load_env():
    env_path = os.path.join(BASE, ".env")
    if not os.path.exists(env_path):
        return
    for line in open(env_path).read().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()

load_env()

from agents.research     import run as run_research
from agents.seo          import run as run_seo
from agents.writer       import run as run_writer
from agents.image_gen    import run as run_image_gen
from agents.sns_pipeline import run as run_sns_pipeline
from agents.publisher    import run as run_publisher

TODAY = datetime.date.today().isoformat()
LOG   = os.path.join(BASE, "output", "logs", f"daily_run_{TODAY}.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)


def log(msg):
    ts = datetime.datetime.utcnow().strftime("[%Y-%m-%d %H:%M UTC]")
    line = f"{ts} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def validate_post_seo(html: str, meta: dict) -> list:
    """SEO 구조 자동 검증 (Step 3.5)
    
    Args:
        html: 생성된 포스트 HTML 전문
        meta: 포스트 메타 데이터 (char_count 등 포함)
    
    Returns:
        issues: 발견된 SEO 문제 리스트 (비어있으면 통과)
    """
    issues = []

    # 필수 구조 검증
    if "<h1" not in html:
        issues.append("H1 없음")

    if "summary-box" not in html:
        issues.append("핵심 요약 박스 없음 (summary-box 클래스 미존재)")

    if 'class="toc"' not in html and "class='toc'" not in html:
        issues.append("ToC 없음 (toc 클래스 미존재)")

    if 'class="faq"' not in html and "class='faq'" not in html:
        issues.append("FAQ 섹션 없음 (faq 클래스 미존재)")

    if "application/ld+json" not in html:
        issues.append("Schema JSON-LD 없음")
    else:
        # Article + FAQPage 두 개 모두 있는지 확인
        ld_count = html.count("application/ld+json")
        if ld_count < 2:
            issues.append(f"Schema JSON-LD 1개만 존재 (Article + FAQPage 두 개 필요)")

    # 외부 링크 수 확인
    external_links = html.count('target="_blank"')
    if external_links < 2:
        issues.append(f"외부 링크 부족 ({external_links}개 < 2개 필수)")

    # 글자수 확인
    char_count = meta.get("char_count", 0)
    if char_count < 3000:
        issues.append(f"글자수 부족 ({char_count:,}자 < 3,000자 필수)")

    # 이미지 alt 텍스트 확인 (alt="" 빈 값 체크)
    empty_alts = len(re.findall(r'<img[^>]*alt\s*=\s*["\']["\']', html))
    if empty_alts > 0:
        issues.append(f"빈 alt 텍스트 이미지 {empty_alts}개 발견")

    # 내부 링크 확인 (상대 경로 링크 기준)
    internal_links = len(re.findall(r'href=["\']/', html)) + len(re.findall(r'href=["\'][^http][^:][^/]', html))
    if internal_links < 2:
        issues.append(f"내부 링크 부족 ({internal_links}개 < 2개 권장)")

    return issues


MOCK_RESEARCH = "--mock-research" in sys.argv


def _make_mock_topics() -> dict:
    """더미 리서치 토픽 생성 (Brave API 없이 테스트용)"""
    return {
        "date": TODAY,
        "topics": [
            {
                "query": "Claude AI 최신 기능 2025",
                "domain": "Claude Anthropic",
                "source": "mock",
                "score": 85,
                "news": [{"title": "Anthropic, Claude 3.7 출시 — 추론 능력 대폭 향상", "url": "https://anthropic.com", "pubdate": TODAY}],
                "web": [{"title": "Claude AI 완벽 가이드", "url": "https://anthropic.com/claude", "snippet": "Claude AI의 최신 기능 완벽 분석"}],
                "papers": [],
                "github": [],
                "collected_at": datetime.datetime.utcnow().isoformat(),
            },
            {
                "query": "AI 에이전트 자동화 워크플로우",
                "domain": "AI 에이전트 자동화",
                "source": "mock",
                "score": 78,
                "news": [{"title": "AI 에이전트로 업무 자동화 300% 향상", "url": "https://example.com", "pubdate": TODAY}],
                "web": [{"title": "AI 에이전트 자동화 가이드", "url": "https://example.com/agent", "snippet": "AI 에이전트를 활용한 업무 자동화 완벽 가이드"}],
                "papers": [],
                "github": [],
                "collected_at": datetime.datetime.utcnow().isoformat(),
            },
            {
                "query": "Gemini 2.0 Flash 성능 분석",
                "domain": "Gemini Google AI",
                "source": "mock",
                "score": 72,
                "news": [{"title": "Google Gemini 2.0 Flash, GPT-4o 속도 2배 앞서", "url": "https://google.com", "pubdate": TODAY}],
                "web": [{"title": "Gemini 2.0 완벽 분석", "url": "https://deepmind.google/gemini", "snippet": "Gemini 2.0의 성능, 속도, 비용 완벽 분석"}],
                "papers": [],
                "github": [],
                "collected_at": datetime.datetime.utcnow().isoformat(),
            },
        ]
    }


def run_pipeline(publish: bool = True):
    log("=" * 60)
    log(f"P004 Daily Pipeline 시작 — {TODAY}")
    if MOCK_RESEARCH:
        log("  모드: --mock-research (더미 토픽 사용)")
    log("=" * 60)

    results = {}
    start_total = time.time()

    # 1. Research
    log("\n[Step 1/4] Research Agent")
    t0 = time.time()
    if MOCK_RESEARCH:
        log("  [Mock] Research 단계 건너뜀 — 더미 토픽 사용")
        topics = _make_mock_topics()
        results["research"] = "ok (mock)"
        log(f"  완료 (mock) — {len(topics.get('topics',[]))}개 주제")
    else:
        try:
            topics = run_research()
            results["research"] = "ok"
            log(f"  완료 ({time.time()-t0:.1f}s) — {len(topics.get('topics',[]))}개 주제")
        except Exception as e:
            log(f"  ❌ 실패: {e}")
            traceback.print_exc()
            results["research"] = f"error: {e}"
            log("  ⚠ Research 실패 — 파이프라인 중단")
            return results

    # 2. SEO
    log("\n[Step 2/4] SEO Agent")
    t0 = time.time()
    try:
        seo = run_seo(topics)
        results["seo"] = "ok"
        log(f"  완료 ({time.time()-t0:.1f}s) — {len(seo.get('seo_plans',[]))}개 SEO 계획")
    except Exception as e:
        log(f"  ❌ 실패: {e}")
        traceback.print_exc()
        results["seo"] = f"error: {e}"
        log("  ⚠ SEO 실패 — 파이프라인 중단 (SEO 없이 Writer 진행 불가)")
        return results

    # 3. Writer
    log("\n[Step 3/4] Writer Agent")
    t0 = time.time()
    try:
        write = run_writer(topics, seo)
        results["writer"] = "ok"
        ok_posts = [p for p in write.get("posts", []) if p.get("char_count", 0) >= 3000]
        log(f"  완료 ({time.time()-t0:.1f}s) — {len(ok_posts)}/3 포스트 3,000자 이상")
        for p in write.get("posts", []):
            log(f"    [{p['post_num']}] {p['title'][:50]} ({p['char_count']:,}자)")
    except Exception as e:
        log(f"  ❌ 실패: {e}")
        traceback.print_exc()
        results["writer"] = f"error: {e}"
        return results

    # 3.5. 이미지 생성
    img_result = None
    log("\n[Step 3.5] Image Gen Agent")
    t0 = time.time()
    try:
        img_result = run_image_gen(write)
        results["image_gen"] = f"{img_result.get('images_generated', 0)}개 생성"
        log(f"  완료 ({time.time()-t0:.1f}s) — {img_result.get('images_generated', 0)}개 포스트 이미지 생성")
        for img_post in img_result.get("posts", []):
            thumb = img_post.get("thumbnail", "")
            card  = img_post.get("card", "")
            upd   = "HTML 교체" if img_post.get("html_updated") else "HTML 미교체"
            log(f"    [{img_post['post_num']}] thumb={os.path.basename(thumb) if thumb else '생략'}"
                f" card={os.path.basename(card) if card else '생략'} {upd}")
    except Exception as e:
        log(f"  ⚠ 이미지 생성 실패 (파이프라인 계속): {e}")
        results["image_gen"] = f"error: {e}"

    # 3.7. SEO 자동 검증
    log("\n[Step 3.7] SEO 자동 검증")
    OUT_P_DIR = os.path.join(BASE, "output", "posts")
    OUT_L_DIR = os.path.join(BASE, "output", "logs")
    os.makedirs(OUT_L_DIR, exist_ok=True)

    seo_validation_results = []
    for post_meta in write.get("posts", []):
        post_num  = post_meta.get("post_num", 1)
        html_file = os.path.join(OUT_P_DIR, post_meta.get("html_file", f"post_{TODAY}_{post_num}.html"))

        if not os.path.exists(html_file):
            log(f"  [{post_num}] ⚠ HTML 파일 없음 — SEO 검증 스킵")
            continue

        html_content = open(html_file, encoding="utf-8").read()
        issues = validate_post_seo(html_content, post_meta)

        validation_entry = {
            "post_num":    post_num,
            "title":       post_meta.get("title", ""),
            "char_count":  post_meta.get("char_count", 0),
            "issues":      issues,
            "passed":      len(issues) == 0,
        }
        seo_validation_results.append(validation_entry)

        if issues:
            log(f"  [{post_num}] ⚠ SEO 이슈 {len(issues)}개:")
            for issue in issues:
                log(f"      - {issue}")
        else:
            log(f"  [{post_num}] ✅ SEO 검증 통과 ({post_meta.get('char_count',0):,}자)")

    # 검증 결과 저장
    validation_log = {
        "date":    TODAY,
        "results": seo_validation_results,
        "summary": {
            "total":  len(seo_validation_results),
            "passed": len([r for r in seo_validation_results if r["passed"]]),
            "failed": len([r for r in seo_validation_results if not r["passed"]]),
        }
    }
    val_log_path = os.path.join(OUT_L_DIR, f"seo_validation_{TODAY}.json")
    with open(val_log_path, "w", encoding="utf-8") as f:
        json.dump(validation_log, f, ensure_ascii=False, indent=2)

    passed_count = validation_log["summary"]["passed"]
    total_count  = validation_log["summary"]["total"]
    log(f"  SEO 검증 완료 — {passed_count}/{total_count} 통과 → {val_log_path}")
    results["seo_validation"] = f"{passed_count}/{total_count} 통과"

    # 3.9. SNS 파이프라인 (변환 + 배포)
    log("\n[Step 3.9] SNS Pipeline Agent")
    t0 = time.time()
    try:
        sns = run_sns_pipeline(write, img_result)
        sns_results = sns.get("results", [])
        ok_threads   = sum(1 for r in sns_results if r.get("formats", {}).get("thread"))
        ok_newsletter = bool(sns.get("newsletter_html"))
        ok_insta     = sum(1 for r in sns_results if r.get("distributed", {}).get("instagram"))
        ok_x         = sum(1 for r in sns_results if r.get("distributed", {}).get("x_thread"))
        ok_yt        = sum(1 for r in sns_results if r.get("distributed", {}).get("youtube"))
        results["sns_pipeline"] = f"스레드={ok_threads} 뉴스레터={'Y' if ok_newsletter else 'N'} IG={ok_insta} X={ok_x} YT={ok_yt}"
        log(f"  완료 ({time.time()-t0:.1f}s) — 스레드:{ok_threads}개 뉴스레터:{'✅' if ok_newsletter else '⚠'} IG:{ok_insta} X:{ok_x} YT:{ok_yt}")
        if sns.get("newsletter_html"):
            log(f"  뉴스레터: {os.path.basename(sns['newsletter_html'])}")
    except Exception as e:
        log(f"  ⚠ SNS 파이프라인 실패 (파이프라인 계속): {e}")
        results["sns_pipeline"] = f"error: {e}"

    # 4. Publisher
    if publish:
        log("\n[Step 4/5] Publisher Agent")
        t0 = time.time()
        try:
            pub = run_publisher(write)
            results["publisher"] = "ok"
            ok_pub = [r for r in pub.get("results", []) if r.get("status") == "published"]
            log(f"  완료 ({time.time()-t0:.1f}s) — {len(ok_pub)}/3 게시 성공")
            for r in pub.get("results", []):
                log(f"    [{r['post_num']}] {r.get('status','')} — {r.get('url','')}")
        except Exception as e:
            log(f"  ❌ 실패: {e}")
            traceback.print_exc()
            results["publisher"] = f"error: {e}"
    else:
        log("\n[Step 4/5] Publisher 생략 (--no-publish 모드)")
        results["publisher"] = "skipped"

    elapsed = time.time() - start_total
    log(f"\n파이프라인 완료 — 총 소요: {elapsed:.1f}s")
    log("=" * 60)
    return results


if __name__ == "__main__":
    publish_flag = "--no-publish" not in sys.argv
    run_pipeline(publish=publish_flag)
