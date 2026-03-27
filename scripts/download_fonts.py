#!/usr/bin/env python3
"""NotoSansKR 폰트 다운로드 스크립트"""
import os, urllib.request, shutil

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE, "assets", "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

# GitHub에서 다운로드할 폰트 (가변폰트 — 기울기 등 모든 weight 포함)
FONTS = {
    "NotoSansKR-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
    "NotoSansKR-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
}

# 시스템 폰트 우선순위 목록 (CJK/한글 지원 폰트)
SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    # 라틴 폴백 (한글 렌더링 불가하지만 ASCII는 OK)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def find_system_font(bold: bool = False) -> str:
    """시스템에서 사용 가능한 폰트 경로 반환"""
    for p in SYSTEM_FONTS:
        if os.path.exists(p):
            return p
    return None


def download_fonts():
    print("[폰트 설치]")
    sys_font = find_system_font()

    if sys_font:
        print(f"  시스템 폰트 발견: {sys_font}")
        for name in ["NotoSansKR-Bold.ttf", "NotoSansKR-Regular.ttf"]:
            dest = os.path.join(FONT_DIR, name)
            if not os.path.exists(dest):
                shutil.copy2(sys_font, dest)
                print(f"  복사: {sys_font} → {dest}")
            else:
                print(f"  이미 존재: {name}")
        return True

    # 시스템 폰트 없으면 GitHub에서 다운로드 시도
    print("  시스템 폰트 미발견 — GitHub에서 다운로드 시도...")
    for name, url in FONTS.items():
        dest = os.path.join(FONT_DIR, name)
        if os.path.exists(dest):
            print(f"  이미 존재: {name}")
            continue
        try:
            print(f"  다운로드: {name}...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            print(f"  완료: {dest} ({len(data)//1024}KB)")
        except Exception as e:
            print(f"  실패: {e}")

    return True


if __name__ == "__main__":
    download_fonts()
    print("\n[완료] 폰트 설치 완료")
    font_files = os.listdir(FONT_DIR)
    print(f"  설치된 파일: {font_files}")
