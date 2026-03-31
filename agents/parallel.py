"""
Parallel Processing Module — P005
SEO / Writer / ImageGen 병렬 처리 유틸리티

변경 이력:
- v1 (2026-03-30): 초기 구현
  * ThreadPoolExecutor 기반 (Claude API I/O 병목 → 스레드 적합)
  * run_seo_parallel(): SEO 분석 3개 동시
  * run_writer_parallel(): 포스트 작성 3개 동시
  * run_image_parallel(): 이미지 생성 3개 동시
  * 예상 효과: 18분 → 6분 (3배 단축)
"""

import concurrent.futures
import time
import traceback
from typing import Callable, Any


def run_parallel(
    fn: Callable,
    items: list,
    max_workers: int = 3,
    label: str = "작업",
) -> list:
    """
    items 리스트의 각 요소에 fn을 병렬 적용.
    반환: 원본 순서 보장된 결과 리스트 (오류 시 None)
    """
    results = [None] * len(items)
    errors  = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(fn, item): idx
            for idx, item in enumerate(items)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                errors[idx] = str(e)
                print(f"  ❌ [{label} {idx+1}] 실패: {e}")
                traceback.print_exc()

    return results, errors


def run_seo_parallel(topics_data: dict) -> dict:
    """
    SEO 분석 병렬 실행.
    agents/seo.py의 analyze_seo를 직접 병렬 호출.
    반환: seo.run()과 동일한 구조
    """
    import datetime
    from agents.seo import analyze_seo, check_seo_quality

    TODAY = datetime.date.today().isoformat()
    topics = topics_data.get("topics", [])

    print(f"[SEO Agent — 병렬] {len(topics)}개 동시 분석 시작")
    t0 = time.time()

    def analyze_one(topic):
        plan = analyze_seo(topic)
        issues = check_seo_quality(plan)
        print(f"  ✅ SEO 완료: {topic.get('query','')[:40]} | 섹션:{len(plan.get('outline',[]))}개 FAQ:{len(plan.get('faq_questions',[]))}개")
        return {"topic": topic["query"], "plan": plan, "issues": issues}

    results, errors = run_parallel(analyze_one, topics, max_workers=3, label="SEO")

    elapsed = time.time() - t0
    print(f"[SEO Agent — 병렬] 완료 ({elapsed:.1f}s) — {len([r for r in results if r])}개 성공")

    # 오류 항목 fallback
    for idx, err in errors.items():
        results[idx] = {"topic": topics[idx].get("query",""), "plan": {}, "issues": [err]}

    return {"date": TODAY, "seo_plans": results}


def run_writer_parallel(topics_data: dict, seo_data: dict) -> dict:
    """
    포스트 작성 병렬 실행 (가장 큰 병목: 937초 → ~310초 예상).
    agents/writer.py의 generate_post를 직접 병렬 호출.
    반환: writer.run()과 동일한 구조
    """
    import os
    import json
    import datetime
    from agents.writer import generate_post, OUT_P

    TODAY = datetime.date.today().isoformat()
    topics   = topics_data.get("topics", [])
    seo_plans = seo_data.get("seo_plans", [])

    pairs = list(zip(topics, seo_plans))
    print(f"[Writer Agent — 병렬] {len(pairs)}개 포스트 동시 작성 시작")
    t0 = time.time()

    def write_one(args):
        idx, (topic, seo_item) = args
        post_num = idx + 1
        post = generate_post(topic, seo_item, post_num)

        # 파일 저장
        fname = f"post_{TODAY}_{post_num}.html"
        fpath = os.path.join(OUT_P, fname)
        os.makedirs(OUT_P, exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(post["html_content"])

        # 메타 저장
        mpath = os.path.join(OUT_P, f"post_{TODAY}_{post_num}_meta.json")
        meta = {k: v for k, v in post.items() if k != "html_content"}
        meta["html_file"] = fname
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        seo_status = "✅ SEO 통과" if not post.get("seo_issues") else f"⚠ {post['seo_issues']}"
        print(f"  [{post_num}] 저장: {fname} ({post['char_count']:,}자) | {seo_status}")
        return meta

    indexed_pairs = list(enumerate(pairs))
    results, errors = run_parallel(write_one, indexed_pairs, max_workers=3, label="Writer")

    elapsed = time.time() - t0
    posts = [r for r in results if r is not None]
    print(f"[Writer Agent — 병렬] 완료 ({elapsed:.1f}s) — {len(posts)}/{len(pairs)}개 작성")

    # write_log 저장
    result = {"date": TODAY, "posts": posts}
    log_path = os.path.join(OUT_P, f"write_log_{TODAY}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    passed = sum(1 for p in posts if not p.get("seo_issues"))
    print(f"  SEO 통과: {passed}/{len(posts)}")
    return result


def run_image_parallel(write_data: dict) -> dict:
    """
    이미지 생성 병렬 실행.
    agents/image_gen.py의 create_thumbnail/create_instagram_card를 직접 병렬 호출.
    반환: image_gen.run()과 동일한 구조
    """
    import os
    import datetime
    from agents.image_gen import (
        create_thumbnail, create_instagram_card,
        upload_to_imgbb, update_html_with_images,
        PIL_OK, BASE
    )

    if not PIL_OK:
        print("[ImageGen — 병렬] ⚠ Pillow 없음 — 이미지 생성 불가")
        return {"error": "Pillow not installed", "images_generated": 0}

    TODAY = datetime.date.today().isoformat()
    date_str = write_data.get("date", TODAY)
    posts = write_data.get("posts", [])

    OUT_IMG_DIR  = os.path.join(BASE, "output", "images")
    OUT_POST_DIR = os.path.join(BASE, "output", "posts")
    os.makedirs(OUT_IMG_DIR, exist_ok=True)

    print(f"[ImageGen — 병렬] {len(posts)}개 이미지 동시 생성 시작")
    t0 = time.time()

    def gen_one(post):
        post_num = post.get("post_num", 1)
        title    = post.get("title", "제목 없음")
        post_with_date = {**post, "date": date_str}

        thumb_name = f"post_{date_str}_{post_num}_thumb.png"
        card_name  = f"post_{date_str}_{post_num}_card.png"
        thumb_path = os.path.join(OUT_IMG_DIR, thumb_name)
        card_path  = os.path.join(OUT_IMG_DIR, card_name)

        thumb_ok = create_thumbnail(post_with_date, thumb_path)
        card_ok  = create_instagram_card(post_with_date, card_path)

        thumb_url = ""
        card_url  = ""
        if thumb_ok:
            thumb_url = upload_to_imgbb(thumb_path) or ""
        if card_ok:
            card_url  = upload_to_imgbb(card_path) or ""

        html_updated = False
        html_file = os.path.join(OUT_POST_DIR, post.get("html_file", f"post_{date_str}_{post_num}.html"))
        if os.path.exists(html_file) and (thumb_url or card_url):
            html_updated = update_html_with_images(html_file, thumb_url, card_url)

        print(f"  [{post_num}] {title[:30]}... thumb={'✅' if thumb_ok else '❌'} card={'✅' if card_ok else '❌'}")
        return {
            "post_num":     post_num,
            "thumbnail":    thumb_path if thumb_ok else "",
            "card":         card_path  if card_ok  else "",
            "thumbnail_url": thumb_url,
            "card_url":     card_url,
            "html_updated": html_updated,
        }

    results, errors = run_parallel(gen_one, posts, max_workers=3, label="ImageGen")

    elapsed = time.time() - t0
    valid = [r for r in results if r]
    generated = sum(1 for r in valid if r.get("thumbnail") or r.get("card"))
    print(f"[ImageGen — 병렬] 완료 ({elapsed:.1f}s) — {generated}개 생성")

    return {"date": date_str, "images_generated": generated, "posts": valid}
