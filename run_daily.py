"""
P005 — 메인 실행 스크립트
매일 자동 실행: Research → SEO(병렬) → Writer(병렬) → ImageGen(병렬) → SEO검증 → Publisher

변경 이력:
- v2 (2026-03-30): 병렬 처리 도입 (18분 → ~6분 예상)
  * SEO 분석 3개 동시 실행
  * 포스트 작성 3개 동시 실행 (가장 큰 병목)
  * 이미지 생성 3개 동시 실행
  * --no-parallel 플래그로 순차 실행 복귀 가능
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
from agents.writer       import run as run_writer, check_seo_structure, inject_missing_seo_sections
from agents.image_gen    import run as run_image_gen
from agents.sns_pipeline import run as run_sns_pipeline
from agents.publisher    import run as run_publisher
from agents.parallel     import run_seo_parallel, run_writer_parallel, run_image_parallel
from agents.quality      import run_quality_check
from agents.viral        import run as run_viral
from agents.angle_refresher import run as run_angle_refresh

# 병렬 처리 기본 활성화 (--no-parallel로 비활성화 가능)
USE_PARALLEL = "--no-parallel" not in sys.argv

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
    """SEO 구조 자동 검증 (Step 3.7)
    writer.py의 check_seo_structure를 기반으로 확장 검증.
    
    Returns:
        issues: 발견된 SEO 문제 리스트 (비어있으면 통과)
    """
    # writer.py의 핵심 4개 구조 검증 (동일 기준)
    issues = list(check_seo_structure(html))

    # 추가 품질 검증
    if "<h1" not in html:
        issues.append("H1 없음")

    # 외부 링크 수 확인
    external_links = html.count('target="_blank"')
    if external_links < 2:
        issues.append(f"외부 링크 부족 ({external_links}개 < 2개 필수)")

    # 글자수 확인
    char_count = meta.get("char_count", 0)
    if char_count < 3000:
        issues.append(f"글자수 부족 ({char_count:,}자 < 3,000자 필수)")

    # 이미지 alt 텍스트 확인
    empty_alts = len(re.findall(r'<img[^>]*alt\s*=\s*["\']["\']', html))
    if empty_alts > 0:
        issues.append(f"빈 alt 텍스트 이미지 {empty_alts}개 발견")

    # 내부 링크 확인
    internal_links = (len(re.findall(r'href=["\']/', html)) +
                      len(re.findall(r'href=["\'][^http][^:][^/]', html)))
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

    # Step 0: 주간 앵글 갱신 (월요일 또는 앵글 파일 없을 때)
    angles_dir = os.path.join(BASE, "output", "angles")
    year_ww    = datetime.date.today().strftime("%Y-W%V")
    angle_file = os.path.join(angles_dir, f"topic_angles_{year_ww}.json")
    is_monday  = datetime.date.today().weekday() == 0

    if is_monday or not os.path.exists(angle_file):
        log("Step 0: 주간 토픽 앵글 갱신 중...")
        try:
            run_angle_refresh()
            log("Step 0: 앵글 갱신 완료")
        except Exception as e:
            log(f"Step 0 ERROR (비치명적, 계속 진행): {e}")
    else:
        log(f"Step 0: 앵글 파일 존재 ({angle_file}), 갱신 스킵")

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

    # 2. SEO (병렬 or 순차)
    mode_label = "병렬" if USE_PARALLEL else "순차"
    log(f"\n[Step 2/4] SEO Agent ({mode_label})")
    t0 = time.time()
    try:
        seo = run_seo_parallel(topics) if USE_PARALLEL else run_seo(topics)
        results["seo"] = "ok"
        plans = seo.get('seo_plans', [])
        log(f"  완료 ({time.time()-t0:.1f}s) — {len(plans)}개 SEO 계획")
        for i, p in enumerate(plans, 1):
            plan = p.get("plan", {})
            log(f"    [{i}] {plan.get('title','')[:50]} | FAQ:{len(plan.get('faq_questions',[]))}개 섹션:{len(plan.get('outline',[]))}개 ✅")
    except Exception as e:
        log(f"  ❌ 실패: {e}")
        traceback.print_exc()
        results["seo"] = f"error: {e}"
        log("  ⚠ SEO 실패 — 파이프라인 중단 (SEO 없이 Writer 진행 불가)")
        return results

    # 3. Writer (병렬 or 순차)
    log(f"\n[Step 3/4] Writer Agent ({mode_label})")
    t0 = time.time()
    try:
        write = run_writer_parallel(topics, seo) if USE_PARALLEL else run_writer(topics, seo)
        results["writer"] = "ok"
        ok_posts = [p for p in write.get("posts", []) if p.get("char_count", 0) >= 3000]
        log(f"  완료 ({time.time()-t0:.1f}s) — {len(ok_posts)}/3 포스트 3,000자 이상")
        for p in write.get("posts", []):
            seo_tag = "✅" if not p.get("seo_issues") else "⚠"
            log(f"    [{p['post_num']}] {seo_tag} {p['title'][:45]} ({p['char_count']:,}자)")
    except Exception as e:
        log(f"  ❌ 실패: {e}")
        traceback.print_exc()
        results["writer"] = f"error: {e}"
        return results

    # 3.5. 이미지 생성 (병렬 or 순차)
    img_result = None
    log(f"\n[Step 3.5] Image Gen Agent ({mode_label})")
    t0 = time.time()
    try:
        img_result = run_image_parallel(write) if USE_PARALLEL else run_image_gen(write)
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

    # 3.8. 콘텐츠 품질 평가
    log("\n[Step 3.8] 콘텐츠 품질 평가")
    try:
        quality = run_quality_check(write, seo)
        summary = quality.get("summary", {})
        avg     = summary.get("avg_score", 0)
        grades  = " / ".join(summary.get("grades", []))
        log(f"  완료 — 평균 {avg:.1f}점 | 등급: {grades}")
        results["quality"] = f"평균 {avg:.1f}점 ({grades})"
    except Exception as e:
        log(f"  ⚠ 품질 평가 실패 (파이프라인 계속): {e}")
        results["quality"] = f"error: {e}"

    # 3.85. Viral Engine (트렌드 감지 + 후킹 스크립트)
    viral_data = {}
    log("\n[Step 3.85] Viral Engine — 트렌드 감지 + 후킹 스크립트")
    t0 = time.time()
    try:
        research_topics = topics.get("topics", []) if topics else []
        viral_result = run_viral(write, research_topics)
        viral_posts  = viral_result.get("posts", [])
        # post_num → viral 데이터 매핑
        viral_data = {p["post_num"]: p for p in viral_posts if "post_num" in p}

        trend_count = len(viral_result.get("trends", {}).get("google_trends", []))
        hook_count  = sum(1 for p in viral_posts if not p.get("error"))
        log(f"  완료 ({time.time()-t0:.1f}s) — 트렌드:{trend_count}개 수집 | 후킹스크립트:{hook_count}개 생성")
        for p in viral_posts:
            if not p.get("error"):
                log(f"    [{p['post_num']}] {p.get('hook_type','?')}형 | 후킹률:{p.get('hook_rate','?')} | 훅: {p.get('hook_text','')[:35]}")
        results["viral"] = f"트렌드:{trend_count} 스크립트:{hook_count}"
    except Exception as e:
        log(f"  ⚠ Viral Engine 실패 (파이프라인 계속): {e}")
        results["viral"] = f"error: {e}"

    # 3.9. SNS 파이프라인 (변환 + 배포, viral_data 전달)
    log("\n[Step 3.9] SNS Pipeline Agent")
    t0 = time.time()
    try:
        sns = run_sns_pipeline(write, img_result)
        sns_results  = sns.get("results", [])
        ok_threads   = sum(1 for r in sns_results if r.get("formats", {}).get("thread"))
        ok_newsletter = bool(sns.get("newsletter_html"))
        ok_insta     = sum(1 for r in sns_results if r.get("distributed", {}).get("instagram"))
        ok_x         = sum(1 for r in sns_results if r.get("distributed", {}).get("x_thread"))
        ok_yt        = sum(1 for r in sns_results if r.get("distributed", {}).get("youtube"))
        results["sns_pipeline"] = f"스레드={ok_threads} 뉴스레터={'Y' if ok_newsletter else 'N'} IG={ok_insta} X={ok_x} YT={ok_yt}"
        log(f"  완료 ({time.time()-t0:.1f}s) — 스레드:{ok_threads}개 뉴스레터:{'✅' if ok_newsletter else '⚠'} IG:{ok_insta} X:{ok_x} YT:{ok_yt}")
        if sns.get("newsletter_html"):
            log(f"  뉴스레터: {os.path.basename(sns['newsletter_html'])}")

        # Viral 후킹 캡션으로 Instagram/YouTube 재발행 (viral_data 있을 때)
        token_exists = os.path.exists(os.path.join(BASE, 'token.json'))
        if viral_data and (os.getenv("INSTAGRAM_ACCESS_TOKEN") or token_exists):
            from agents.distributors.instagram_bot import publish as ig_publish
            from agents.distributors.youtube_bot   import publish_shorts as yt_publish
            from agents.distributors.image_host    import get_public_url

            for post_meta in write.get("posts", []):
                pnum     = post_meta.get("post_num", 1)
                vd       = viral_data.get(pnum)
                if not vd:
                    continue

                # Instagram: 카드 이미지 + 후킹 캡션
                img_info = next((p for p in (img_result or {}).get("posts", []) if p.get("post_num") == pnum), {})
                card_path = img_info.get("card", "")
                if card_path and os.getenv("INSTAGRAM_ACCESS_TOKEN"):
                    ok = ig_publish(post_meta, image_path_or_url=card_path, viral_data=vd)
                    log(f"  IG [{pnum}]: {'✅ 발행' if ok else '❌ 실패'}")

                # YouTube Shorts: 영상 + 후킹 제목 + 자막
                shorts_dir  = BASE / "output" / "shorts"
                today_str   = TODAY
                slug        = post_meta.get("slug", f"post-{pnum}")
                video_path  = str(shorts_dir / f"{today_str}_{slug}_shorts.mp4")
                srt_path    = str(BASE / "output" / "viral" / f"post_{today_str}_{pnum}.srt")
                thumb_path  = img_info.get("thumbnail", "")
                if os.path.exists(video_path) and os.getenv("YOUTUBE_CHANNEL_ID"):
                    ok = yt_publish(post_meta, video_path, thumb_path, srt_path, viral_data=vd)
                    log(f"  YT [{pnum}]: {'✅ 발행' if ok else '❌ 실패'}")

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
