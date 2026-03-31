"""
Research Agent — P004 (개선판 v2)
매일 최신 AI 트렌드 기반으로 주제 3개 발굴 + 자료 수집

개선 사항:
- 중복방지 강화: 임계값 0.35 + bigram + 핵심 단어 3개 이상 겹치면 무조건 중복
- AI 도메인 60+개로 확장
- 날짜 seed 기반 도메인 로테이션 시스템 (매일 20개 선택, 전체 순환)
- 신규 채널: HackerNews, Reddit, ProductHunt, arXiv 주간
- 포지셔닝 다양화: 뉴스성 / 기술심층 / 산업분석 / 실용가이드 / 트렌드분석 / 국내이슈
- 이력 DB 통합: p004-blogger/posts/*.md frontmatter + output/published/*.json
"""
import os, json, datetime, time, urllib.request, urllib.parse, re, hashlib
import xml.etree.ElementTree as ET

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "output", "topics")
POSTS  = os.path.join(BASE, "output", "posts")

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
TODAY = datetime.date.today().isoformat()

# ── AI 도메인 카테고리 (60+개) ─────────────────────────────────────────────

AI_DOMAINS = [
    # 기존 15개
    "ChatGPT OpenAI",
    "Claude Anthropic",
    "Gemini Google AI",
    "Manus AI 에이전트",
    "LLM 언어모델",
    "AI 에이전트 자동화",
    "멀티모달 AI",
    "AI 코딩 개발",
    "프롬프트 엔지니어링",
    "AI 논문 연구",
    "딥러닝 머신러닝",
    "AI 생산성 활용",
    "RAG 벡터DB",
    "오픈소스 AI 모델",
    "AI 규제 정책",

    # AI 모델/서비스
    "Grok xAI",
    "Llama Meta AI",
    "Mistral AI",
    "Perplexity AI",
    "Copilot Microsoft AI",
    "DeepSeek AI 모델",
    "Qwen Alibaba AI",
    "Phi Microsoft 소형LLM",
    "Command R Cohere",
    "Stable Diffusion 이미지생성",
    "Midjourney AI 아트",
    "DALL-E OpenAI 이미지",
    "Runway Gen AI 영상",
    "Sora OpenAI 영상생성",
    "ElevenLabs AI 음성",
    "Whisper 음성인식",
    "HuggingFace 오픈소스",

    # AI 응용/산업
    "AI 헬스케어 의료",
    "AI 교육 에듀테크",
    "AI 법률 리걸테크",
    "AI 금융 핀테크",
    "AI 부동산",
    "AI 마케팅 광고",
    "AI 게임 개발",
    "AI 음악 작곡",
    "AI 영상편집",
    "AI 번역 언어",
    "AI 검색엔진",
    "AI 사이버보안",
    "AI 로보틱스 자율주행",
    "AI 제조 스마트팩토리",
    "AI 농업 푸드테크",

    # AI 기술/개념
    "파인튜닝 LoRA PEFT",
    "양자화 GGUF llama.cpp",
    "컨텍스트 윈도우 LLM",
    "AI 할루시네이션 해결",
    "Mixture of Experts MoE",
    "AI 멀티에이전트 시스템",
    "컴퓨터 비전 YOLO",
    "강화학습 RLHF",
    "AI 워크플로우 n8n",
    "벡터 데이터베이스 Pinecone Chroma",
    "LangChain LlamaIndex",
    "AI API 통합",
    "엣지 AI 온디바이스",
    "AI 칩 반도체 NVIDIA",
    "Transformer 아키텍처",

    # AI 트렌드/비즈니스
    "AI 스타트업 투자",
    "AI 일자리 취업",
    "AI 윤리 편향",
    "AI 저작권 지적재산",
    "AI 규제 EU AI Act",
    "AI 데이터센터 전력",
    "오픈소스 vs 클로즈드 AI",
    "AI 구독 서비스 비교",
    "AI 생산성 측정",
    "AI PC 노트북 추천",
    "AI 스마트폰 온디바이스",
    "AI 웨어러블",

    # 한국/글로벌 AI
    "한국 AI 정책 NIPA",
    "네이버 CLOVA AI",
    "카카오 AI",
    "삼성 AI",
    "SK AI 투자",
    "KT AI",
    "국내 AI 스타트업",
]

DAILY_DOMAINS_COUNT = 20

# ── 포지셔닝 매핑 ──────────────────────────────────────────────────────────

DOMAIN_POSITIONING = {
    # 뉴스성
    "ChatGPT OpenAI":          "뉴스성",
    "Claude Anthropic":        "뉴스성",
    "Gemini Google AI":        "뉴스성",
    "Grok xAI":                "뉴스성",
    "DeepSeek AI 모델":        "뉴스성",
    "Sora OpenAI 영상생성":    "뉴스성",
    "Manus AI 에이전트":       "뉴스성",
    "Perplexity AI":           "뉴스성",
    "Copilot Microsoft AI":    "뉴스성",
    "Llama Meta AI":           "뉴스성",
    "Mistral AI":              "뉴스성",
    "Qwen Alibaba AI":         "뉴스성",

    # 기술심층
    "LLM 언어모델":                    "기술심층",
    "멀티모달 AI":                      "기술심층",
    "AI 코딩 개발":                     "기술심층",
    "프롬프트 엔지니어링":              "기술심층",
    "AI 논문 연구":                     "기술심층",
    "딥러닝 머신러닝":                  "기술심층",
    "RAG 벡터DB":                       "기술심층",
    "파인튜닝 LoRA PEFT":               "기술심층",
    "양자화 GGUF llama.cpp":            "기술심층",
    "컨텍스트 윈도우 LLM":             "기술심층",
    "AI 할루시네이션 해결":             "기술심층",
    "Mixture of Experts MoE":           "기술심층",
    "AI 멀티에이전트 시스템":           "기술심층",
    "컴퓨터 비전 YOLO":                 "기술심층",
    "강화학습 RLHF":                    "기술심층",
    "벡터 데이터베이스 Pinecone Chroma": "기술심층",
    "LangChain LlamaIndex":             "기술심층",
    "Transformer 아키텍처":             "기술심층",
    "HuggingFace 오픈소스":             "기술심층",
    "Phi Microsoft 소형LLM":            "기술심층",
    "Command R Cohere":                 "기술심층",
    "Whisper 음성인식":                 "기술심층",
    "ElevenLabs AI 음성":               "기술심층",
    "Stable Diffusion 이미지생성":      "기술심층",
    "Midjourney AI 아트":               "기술심층",
    "DALL-E OpenAI 이미지":             "기술심층",
    "Runway Gen AI 영상":               "기술심층",
    "AI 칩 반도체 NVIDIA":              "기술심층",
    "엣지 AI 온디바이스":               "기술심층",

    # 산업분석
    "AI 헬스케어 의료":     "산업분석",
    "AI 교육 에듀테크":     "산업분석",
    "AI 법률 리걸테크":     "산업분석",
    "AI 금융 핀테크":       "산업분석",
    "AI 부동산":            "산업분석",
    "AI 마케팅 광고":       "산업분석",
    "AI 게임 개발":         "산업분석",
    "AI 음악 작곡":         "산업분석",
    "AI 영상편집":          "산업분석",
    "AI 번역 언어":         "산업분석",
    "AI 검색엔진":          "산업분석",
    "AI 사이버보안":        "산업분석",
    "AI 로보틱스 자율주행": "산업분석",
    "AI 제조 스마트팩토리": "산업분석",
    "AI 농업 푸드테크":     "산업분석",

    # 실용가이드
    "AI 에이전트 자동화":  "실용가이드",
    "AI 생산성 활용":      "실용가이드",
    "AI 워크플로우 n8n":   "실용가이드",
    "AI API 통합":         "실용가이드",
    "AI PC 노트북 추천":   "실용가이드",
    "AI 스마트폰 온디바이스": "실용가이드",
    "AI 웨어러블":         "실용가이드",
    "AI 구독 서비스 비교": "실용가이드",

    # 트렌드분석
    "AI 스타트업 투자":      "트렌드분석",
    "AI 일자리 취업":        "트렌드분석",
    "AI 윤리 편향":          "트렌드분석",
    "AI 저작권 지적재산":    "트렌드분석",
    "AI 규제 EU AI Act":     "트렌드분석",
    "AI 데이터센터 전력":    "트렌드분석",
    "오픈소스 vs 클로즈드 AI": "트렌드분석",
    "AI 생산성 측정":        "트렌드분석",
    "AI 규제 정책":          "트렌드분석",
    "오픈소스 AI 모델":      "트렌드분석",

    # 국내이슈
    "한국 AI 정책 NIPA": "국내이슈",
    "네이버 CLOVA AI":   "국내이슈",
    "카카오 AI":         "국내이슈",
    "삼성 AI":           "국내이슈",
    "SK AI 투자":        "국내이슈",
    "KT AI":             "국내이슈",
    "국내 AI 스타트업":  "국내이슈",
}

CONTENT_ANGLES = {
    "뉴스성":   "오늘 일어난 일 → 의미 → 독자 영향 분석",
    "기술심층": "개념 설명 → 작동 원리 → 실습 예시 → 한계와 대안",
    "산업분석": "현황 파악 → 주요 플레이어 → 시장 전망 → 독자 기회",
    "실용가이드": "왜 써야 하나 → 단계별 방법 → 실전 팁 → 주의사항",
    "트렌드분석": "트렌드 배경 → 데이터 근거 → 시사점 → 미래 예측",
    "국내이슈":  "국내 배경 → 현황 → 해외 비교 → 시사점과 전망",
}

# ── 도메인별 세부 토픽 앵글 ────────────────────────────────────────────────
# 각 도메인 카테고리 안에서 독립 포스팅이 가능한 세부 주제들
# generate_trending_queries() 에서 날짜 기반으로 1개 선택 → 검색 쿼리에 결합
TOPIC_SUBTYPES = {
    "ChatGPT OpenAI": [
        "최신 업데이트 변경사항",
        "API 비용 계산 및 최적화",
        "Custom GPT 만들기 실전",
        "프롬프트 엔지니어링 실전 템플릿",
        "o3/o4 추론 모델 심층 분석",
        "업무별 활용 사례 (회계/법무/마케팅)",
        "ChatGPT vs 경쟁사 성능 벤치마크",
        "플러그인 및 GPT Store 추천",
        "코딩 어시스턴트로 활용하기",
        "ChatGPT 한국어 성능 분석",
        "엔터프라이즈 도입 사례",
        "무료 vs 유료 플랜 비교",
        "보안 및 개인정보 이슈",
        "교육 현장 활용 방법",
        "ChatGPT로 콘텐츠 제작하기",
    ],
    "Claude Anthropic": [
        "Claude 최신 버전 기능 변경사항",
        "Claude vs ChatGPT 실전 비교",
        "긴 문서 분석에 Claude 활용하기",
        "Claude API 연동 실습",
        "Constitutional AI 안전성 원리",
        "코드 리뷰 및 디버깅 활용법",
        "Claude Projects 기능 완벽 가이드",
        "Claude 한국어 성능 심층 테스트",
        "연구/논문 작성에 Claude 쓰기",
        "Claude Computer Use 실전 활용",
        "Artifacts 기능으로 앱 만들기",
        "비용 대비 성능 최적화",
        "Claude 모델 선택 가이드 (Haiku/Sonnet/Opus)",
        "멀티턴 대화 전략",
    ],
    "Gemini Google AI": [
        "Gemini 최신 버전 업데이트",
        "Gemini vs GPT-4 성능 비교",
        "Google Workspace 통합 활용",
        "Gemini Advanced 기능 완전 분석",
        "멀티모달 능력 심층 테스트",
        "Gemini API로 앱 만들기",
        "Google Search에서 AI 활용",
        "Gemini 코딩 어시스턴트 활용",
        "NotebookLM 실전 활용법",
        "Gemini Flash vs Pro 선택 기준",
        "Android AI 기능 활용하기",
        "Gemini 한국어 성능 평가",
        "기업용 Gemini for Business",
    ],
    "Grok xAI": [
        "Grok 최신 기능 업데이트",
        "Grok vs ChatGPT 실전 비교",
        "실시간 인터넷 검색 기능 활용",
        "X(트위터) 통합 AI 활용법",
        "Grok 무료 사용 방법",
        "Grok API 활용하기",
        "Grok의 검열 없는 응답 특징 분석",
        "Grok 이미지 생성 기능",
        "SuperGrok 구독 가치 분석",
    ],
    "Llama Meta AI": [
        "Llama 최신 모델 성능 분석",
        "로컬에서 Llama 실행하기",
        "Llama 파인튜닝 실전 가이드",
        "Meta AI 서비스 활용법",
        "Llama.cpp로 PC에서 돌리기",
        "Llama vs GPT 오픈소스 비교",
        "Llama 기반 맞춤형 AI 만들기",
        "Llama Guard 안전성 적용",
        "기업용 Llama 도입 사례",
        "Llama 멀티언어 성능 테스트",
    ],
    "Mistral AI": [
        "Mistral 모델 라인업 정리",
        "Mistral vs Llama 성능 비교",
        "Mixtral MoE 아키텍처 설명",
        "로컬 실행 방법 완전 가이드",
        "Mistral API 활용 실습",
        "유럽 AI의 강자 Mistral 분석",
        "Mistral 파인튜닝 가이드",
        "Le Chat 서비스 활용법",
        "비용 효율 최고 모델 선택",
    ],
    "DeepSeek AI 모델": [
        "DeepSeek 최신 모델 성능 분석",
        "DeepSeek vs GPT-4 비교",
        "DeepSeek 로컬 실행 가이드",
        "DeepSeek R1 추론 능력 분석",
        "중국 AI의 급부상 배경 분석",
        "DeepSeek API 연동 실습",
        "DeepSeek 보안 이슈 정리",
        "DeepSeek 오픈소스 활용하기",
        "DeepSeek Coder 코딩 활용",
    ],
    "Perplexity AI": [
        "Perplexity AI 완전 활용 가이드",
        "Perplexity vs Google 검색 비교",
        "Perplexity Pro 기능 분석",
        "AI 검색의 미래 Perplexity 분석",
        "Perplexity API 연동",
        "리서치 자동화에 Perplexity 쓰기",
        "Perplexity Space 기능 활용",
        "할루시네이션 최소화 전략",
    ],
    "Copilot Microsoft AI": [
        "Microsoft Copilot 전 제품 정리",
        "GitHub Copilot 코딩 활용법",
        "Word/Excel/PowerPoint Copilot 실전",
        "Microsoft 365 Copilot 도입 가이드",
        "Copilot Studio 커스터마이징",
        "Azure AI 서비스 연동",
        "Teams AI 기능 활용",
        "Copilot+ PC 기능 완전 분석",
        "Copilot vs ChatGPT 기업용 비교",
    ],
    "Qwen Alibaba AI": [
        "Qwen 모델 성능 벤치마크",
        "Qwen 로컬 실행 방법",
        "중국 오픈소스 AI 현황",
        "Qwen VL 멀티모달 기능",
        "Qwen API 활용하기",
        "Qwen 한국어 성능 테스트",
        "알리바바 AI 전략 분석",
    ],
    "Stable Diffusion 이미지생성": [
        "Stable Diffusion 완전 초보 가이드",
        "AUTOMATIC1111 vs ComfyUI 비교",
        "LoRA 모델 적용 실전",
        "프롬프트 작성법 마스터하기",
        "최신 모델 SDXL/SD3 분석",
        "Control Net 활용 완벽 가이드",
        "인물 사진 생성 고급 기법",
        "상업적 이용 가능한 모델 정리",
        "로컬 vs 클라우드 실행 비교",
        "AI 이미지 저작권 이슈",
        "실사 vs 애니메이션 스타일 설정",
    ],
    "Midjourney AI 아트": [
        "Midjourney v7 완전 가이드",
        "프롬프트 마스터 클래스",
        "Midjourney로 상업용 이미지 만들기",
        "스타일 일관성 유지하기",
        "캐릭터 디자인 실전",
        "Midjourney vs DALL-E vs Stable Diffusion",
        "웹툰/만화 스타일 생성",
        "로고 및 브랜딩에 활용",
        "Midjourney 구독 플랜 비교",
        "인스타그램 콘텐츠 제작",
    ],
    "DALL-E OpenAI 이미지": [
        "DALL-E 3 완전 활용 가이드",
        "ChatGPT에서 이미지 생성하기",
        "DALL-E API 연동 실습",
        "텍스트 포함 이미지 생성 팁",
        "DALL-E vs Midjourney 비교",
        "상업 목적 이용 가이드",
        "이미지 편집 기능 inpainting",
    ],
    "Runway Gen AI 영상": [
        "Runway Gen-3 영상 생성 가이드",
        "AI 영상 제작 워크플로우",
        "Runway vs Sora 비교",
        "영화/광고 제작에 AI 활용",
        "Runway API 연동",
        "모션 브러시 기능 활용",
        "AI 영상 편집 실전 팁",
    ],
    "Sora OpenAI 영상생성": [
        "Sora 최신 기능 및 업데이트",
        "Sora 접근 방법 가이드",
        "Sora로 영상 제작 실전",
        "Sora vs Runway vs Pika 비교",
        "AI 영상 생성 미래 전망",
        "영상 제작 산업 변화 분석",
        "Sora 프롬프트 최적화",
    ],
    "ElevenLabs AI 음성": [
        "ElevenLabs 완전 활용 가이드",
        "음성 복제(Voice Cloning) 실전",
        "팟캐스트 AI 제작 워크플로우",
        "ElevenLabs API 연동 실습",
        "AI 더빙 실전 활용",
        "TTS 서비스 비교 (ElevenLabs vs 경쟁사)",
        "한국어 AI 음성 품질 분석",
        "유튜브 AI 나레이션 제작",
    ],
    "Whisper 음성인식": [
        "Whisper 로컬 실행 완전 가이드",
        "회의록 자동화 실전",
        "Whisper API 연동",
        "한국어 인식 정확도 테스트",
        "실시간 자막 생성 방법",
        "Whisper vs 경쟁 STT 비교",
        "영상 자동 자막 생성 워크플로우",
        "다국어 번역 동시 처리",
    ],
    "HuggingFace 오픈소스": [
        "HuggingFace 완전 초보 가이드",
        "모델 허브에서 모델 불러오기",
        "Transformers 라이브러리 실습",
        "Spaces로 AI 앱 배포하기",
        "HuggingFace로 파인튜닝하기",
        "Inference API 활용",
        "Datasets 라이브러리 활용",
        "오픈소스 AI 생태계 분석",
        "HuggingFace Pro 기능 정리",
    ],
    "LLM 언어모델": [
        "LLM 작동 원리 쉽게 이해하기",
        "LLM 성능 벤치마크 완전 정리",
        "LLM 선택 가이드 (용도별)",
        "LLM 파인튜닝 vs RAG 비교",
        "LLM 환각(hallucination) 원인과 해결",
        "소형 LLM(SLM) 활용 사례",
        "LLM 컨텍스트 길이 활용법",
        "LLM API 비용 비교",
        "멀티모달 LLM 최신 동향",
        "LLM 보안 취약점 분석",
    ],
    "멀티모달 AI": [
        "멀티모달 AI 개념 완전 정리",
        "이미지+텍스트 AI 활용 사례",
        "영상 이해 AI 최신 동향",
        "음성+비전 멀티모달 실전",
        "멀티모달 모델 성능 비교",
        "멀티모달 API 연동 실습",
        "실무에서 멀티모달 AI 쓰기",
    ],
    "AI 코딩 개발": [
        "AI 코딩 툴 완전 비교 (Copilot/Cursor/Cline)",
        "Cursor AI 완전 활용 가이드",
        "AI로 풀스택 앱 만들기",
        "코드 리뷰 자동화 실전",
        "AI 페어 프로그래밍 워크플로우",
        "테스트 코드 자동 생성",
        "레거시 코드 리팩토링 AI 활용",
        "AI 코딩 보안 이슈 주의점",
        "개발자 생산성 AI 도구 모음",
        "Devin AI 에이전트 분석",
        "Windsurf vs Cursor 비교",
        "AI로 API 문서 자동화",
    ],
    "프롬프트 엔지니어링": [
        "프롬프트 엔지니어링 기초 완전 정리",
        "Chain of Thought 프롬프트 실전",
        "Few-shot vs Zero-shot 비교",
        "역할 부여(Role Prompting) 고급 기법",
        "업무별 프롬프트 템플릿 모음",
        "프롬프트 인젝션 공격과 방어",
        "시스템 프롬프트 설계 전략",
        "출력 형식 제어 기법",
        "프롬프트 최적화 자동화",
        "멀티턴 대화 프롬프트 설계",
    ],
    "딥러닝 머신러닝": [
        "딥러닝 vs 머신러닝 차이 완전 정리",
        "CNN 이미지 인식 원리",
        "RNN/LSTM 시계열 분석",
        "GAN 생성 모델 원리",
        "모델 학습 최적화 기법",
        "과적합 방지 실전 전략",
        "PyTorch vs TensorFlow 비교",
        "ML 파이프라인 구축",
        "데이터 전처리 실전",
        "ML 모델 배포(MLOps)",
    ],
    "RAG 벡터DB": [
        "RAG 완전 초보 가이드",
        "벡터 데이터베이스 종류 비교",
        "RAG vs 파인튜닝 선택 기준",
        "RAG 시스템 구축 실전",
        "임베딩 모델 선택 가이드",
        "RAG 성능 최적화 기법",
        "Hybrid Search 구현",
        "기업 문서 RAG 구축 사례",
        "RAG 평가 지표 및 방법",
        "GraphRAG 최신 동향",
    ],
    "파인튜닝 LoRA PEFT": [
        "파인튜닝 vs RAG 완전 비교",
        "LoRA 원리 쉽게 이해하기",
        "QLoRA로 저사양 GPU 파인튜닝",
        "파인튜닝 데이터셋 준비 방법",
        "Unsloth로 빠른 파인튜닝",
        "파인튜닝 평가 및 검증",
        "도메인 특화 모델 만들기",
        "파인튜닝 비용 최소화 전략",
        "PEFT 기법 총정리",
    ],
    "양자화 GGUF llama.cpp": [
        "양자화 개념 쉽게 이해하기",
        "GGUF 파일 포맷 완전 정리",
        "llama.cpp 설치 및 실행 가이드",
        "Ollama로 로컬 AI 구축",
        "양자화 Q4 vs Q8 성능 비교",
        "CPU에서 LLM 실행하기",
        "저사양 PC에서 AI 돌리기",
        "LM Studio 완전 활용 가이드",
        "모델 양자화 직접 해보기",
    ],
    "컨텍스트 윈도우 LLM": [
        "컨텍스트 윈도우란 무엇인가",
        "긴 컨텍스트 모델 비교 (128K/200K/1M)",
        "컨텍스트 윈도우 효율 활용법",
        "Lost in the Middle 문제 해결",
        "긴 문서 처리 전략",
        "컨텍스트 압축 기법",
        "RAG vs 긴 컨텍스트 선택 기준",
    ],
    "AI 할루시네이션 해결": [
        "AI 환각(hallucination) 원인 완전 분석",
        "환각 감지 및 검증 방법",
        "팩트 체크 AI 도구 모음",
        "RAG로 환각 줄이기",
        "프롬프트로 환각 최소화",
        "의료/법률 AI 신뢰성 문제",
        "환각 평가 벤치마크 분석",
        "Citation 포함 AI 응답 만들기",
    ],
    "Mixture of Experts MoE": [
        "MoE 아키텍처 원리 설명",
        "GPT-4의 MoE 구조 분석",
        "MoE vs Dense 모델 비교",
        "Mixtral MoE 실전 활용",
        "MoE 모델 로컬 실행",
        "MoE의 장단점 완전 분석",
        "MoE 최신 연구 동향",
    ],
    "AI 멀티에이전트 시스템": [
        "멀티에이전트 시스템 개념 정리",
        "AutoGen 완전 활용 가이드",
        "CrewAI 실전 구축",
        "에이전트 오케스트레이션 전략",
        "멀티에이전트 vs 단일에이전트",
        "에이전트 메모리 관리",
        "자율 AI 에이전트 위험성",
        "기업 업무 자동화 에이전트 구축",
        "에이전트 평가 방법",
    ],
    "컴퓨터 비전 YOLO": [
        "YOLO 최신 버전 완전 정리",
        "객체 감지 실전 프로젝트",
        "얼굴 인식 AI 구현",
        "의료 영상 분석 AI",
        "자율주행 비전 시스템",
        "CCTV AI 분석 시스템 구축",
        "OpenCV + AI 실전",
        "이미지 분류 모델 만들기",
        "비전 AI 상업 활용 사례",
    ],
    "강화학습 RLHF": [
        "강화학습 기초 완전 정리",
        "RLHF란 무엇인가",
        "ChatGPT가 RLHF를 쓰는 이유",
        "DPO vs RLHF 비교",
        "게임 AI 강화학습 사례",
        "로봇 제어 강화학습",
        "강화학습 최신 연구 동향",
        "PPO 알고리즘 설명",
    ],
    "AI 워크플로우 n8n": [
        "n8n 완전 초보 가이드",
        "n8n vs Zapier vs Make 비교",
        "n8n으로 AI 자동화 구축",
        "n8n 셀프호스팅 설치 가이드",
        "업무 자동화 실전 사례 10개",
        "AI Agent 노드 활용",
        "n8n + Claude/ChatGPT 연동",
        "노코드 AI 자동화 워크플로우",
        "n8n 템플릿 추천 모음",
    ],
    "벡터 데이터베이스 Pinecone Chroma": [
        "벡터 DB 완전 비교 (Pinecone/Chroma/Weaviate/Qdrant)",
        "Chroma 로컬 설치 실습",
        "Pinecone 클라우드 활용 가이드",
        "벡터 임베딩 이해하기",
        "벡터 DB 성능 최적화",
        "벡터 DB 비용 비교",
        "RAG 시스템에 벡터 DB 연동",
        "시맨틱 검색 구현하기",
    ],
    "LangChain LlamaIndex": [
        "LangChain 완전 초보 가이드",
        "LlamaIndex vs LangChain 비교",
        "LangChain으로 RAG 구축",
        "LangGraph 에이전트 워크플로우",
        "LlamaIndex 문서 분석 실전",
        "LangChain 비용 최적화",
        "LangSmith 모니터링 활용",
        "LangChain 최신 버전 변경사항",
        "프로덕션 LangChain 배포",
    ],
    "AI API 통합": [
        "OpenAI API 완전 가이드",
        "API 비용 최적화 전략",
        "여러 AI API 동시 활용",
        "AI API 보안 처리",
        "API Rate Limit 대응",
        "Streaming 응답 구현",
        "Function Calling 실전",
        "AI API 오류 처리 전략",
        "API 모니터링 및 로깅",
    ],
    "엣지 AI 온디바이스": [
        "온디바이스 AI 개념 정리",
        "Apple Silicon AI 성능 분석",
        "Snapdragon X AI 기능",
        "스마트폰 AI 비교",
        "엣지 AI 프라이버시 장점",
        "온디바이스 AI 개발 가이드",
        "TensorFlow Lite 실전",
        "엣지 AI 산업 활용 사례",
    ],
    "AI 칩 반도체 NVIDIA": [
        "NVIDIA GPU AI 시장 현황",
        "H100 vs A100 vs RTX 성능 비교",
        "AMD vs NVIDIA AI 칩 경쟁",
        "AI 칩 공급망 분석",
        "구글 TPU vs NVIDIA GPU",
        "AI 반도체 투자 전망",
        "개인용 GPU AI 추천",
        "AI 데이터센터 칩 트렌드",
        "한국 AI 반도체 현황",
    ],
    "Transformer 아키텍처": [
        "Transformer 원리 쉽게 이해하기",
        "Attention 메커니즘 완전 설명",
        "GPT vs BERT 구조 비교",
        "Transformer 최신 변형 모델",
        "Vision Transformer(ViT) 분석",
        "Transformer 효율화 기법",
        "Transformer 코드 직접 구현",
        "Transformer가 바꾼 AI 세계",
    ],
    "AI 에이전트 자동화": [
        "AI 에이전트 개념 완전 정리",
        "업무 자동화 AI 에이전트 구축",
        "이메일 자동화 에이전트",
        "데이터 수집 자동화",
        "보고서 자동 생성 에이전트",
        "AI 에이전트 보안 이슈",
        "에이전트 프레임워크 비교",
        "노코드 AI 에이전트 도구",
        "에이전트 실패 사례 분석",
        "AI 에이전트 ROI 측정",
    ],
    "AI 생산성 활용": [
        "AI로 업무 효율 2배 높이기",
        "직장인 AI 도구 모음 추천",
        "글쓰기 AI 도구 비교",
        "회의 요약 AI 완전 가이드",
        "AI로 이메일 자동화",
        "프리랜서 AI 활용 전략",
        "AI 생산성 앱 TOP 10",
        "AI 아침 루틴 만들기",
        "재택근무 AI 도구 추천",
        "팀 협업 AI 도구 활용",
    ],
    "AI 헬스케어 의료": [
        "AI 의료 진단 최신 현황",
        "AI 신약 개발 사례",
        "의료 AI 규제 현황",
        "AI 암 진단 정확도 분석",
        "병원 AI 도입 사례",
        "개인 건강관리 AI 앱",
        "AI 정신건강 서비스",
        "의료 영상 AI 분석",
        "AI 의사 미래 가능성",
        "한국 의료 AI 현황",
    ],
    "AI 교육 에듀테크": [
        "AI 튜터 서비스 비교",
        "Khan Academy AI 활용",
        "학교에서 AI 규제 현황",
        "AI로 맞춤형 학습",
        "AI 작문 도구 교육 활용",
        "대학 AI 도입 사례",
        "AI 영어 회화 앱 추천",
        "학생 AI 활용 윤리",
        "AI 코딩 교육 플랫폼",
        "에듀테크 AI 스타트업",
    ],
    "AI 법률 리걸테크": [
        "AI 법률 서비스 현황",
        "계약서 자동 검토 AI",
        "법률 AI 정확도 분석",
        "변호사 AI 활용 사례",
        "AI 판결 예측 시스템",
        "법률 챗봇 서비스 비교",
        "리걸테크 스타트업 투자 현황",
        "AI 특허 출원 자동화",
        "법률 AI 윤리 문제",
    ],
    "AI 금융 핀테크": [
        "AI 투자 자문 서비스 비교",
        "AI 주식 예측 가능한가",
        "은행 AI 도입 현황",
        "AI 사기 탐지 시스템",
        "AI 신용 평가 모델",
        "알고리즘 트레이딩 AI",
        "AI 개인 재무 관리 앱",
        "핀테크 AI 규제 현황",
        "AI 보험 언더라이팅",
        "한국 금융 AI 현황",
    ],
    "AI 마케팅 광고": [
        "AI 마케팅 도구 완전 비교",
        "AI 광고 카피 작성 실전",
        "SEO AI 도구 활용",
        "AI 개인화 마케팅 전략",
        "소셜미디어 AI 자동화",
        "AI 이메일 마케팅 최적화",
        "광고 크리에이티브 AI 생성",
        "AI A/B 테스트 자동화",
        "AI 마케팅 ROI 분석",
        "콘텐츠 마케팅 AI 워크플로우",
    ],
    "AI 게임 개발": [
        "AI 게임 개발 도구 현황",
        "NPC AI 고도화 사례",
        "Unity AI 기능 활용",
        "AI로 게임 에셋 제작",
        "절차적 생성 AI 기법",
        "게임 테스팅 AI 자동화",
        "AI 게임 시나리오 작성",
        "AI 플레이어 행동 분석",
        "인디 개발자 AI 활용",
    ],
    "AI 음악 작곡": [
        "AI 음악 생성 도구 비교 (Suno/Udio/Stable Audio)",
        "Suno AI로 노래 만들기",
        "AI 작곡 실전 워크플로우",
        "AI 음악 저작권 이슈",
        "음악가 AI 협업 사례",
        "AI 음악 마스터링",
        "유튜브 AI 배경음악 제작",
        "AI 음악의 미래 전망",
    ],
    "AI 영상편집": [
        "AI 영상 편집 도구 비교",
        "Adobe AI 기능 완전 가이드",
        "자동 자막 생성 AI",
        "AI 영상 배경 제거",
        "CapCut AI 기능 활용",
        "유튜브 편집 AI 자동화",
        "AI 썸네일 생성",
        "영상 색보정 AI 도구",
        "AI로 숏폼 영상 제작",
    ],
    "AI 번역 언어": [
        "AI 번역 서비스 비교 (DeepL/Papago/Google)",
        "LLM 번역 품질 분석",
        "전문 분야 AI 번역 정확도",
        "AI 동시통역 현황",
        "번역 AI vs 인간 번역사",
        "다국어 AI 모델 활용",
        "AI 자막 번역 자동화",
        "한국어 특화 AI 번역",
    ],
    "AI 검색엔진": [
        "AI 검색의 미래 분석",
        "Perplexity vs Google SGE 비교",
        "AI 검색이 SEO에 미치는 영향",
        "Microsoft Bing AI 검색 활용",
        "AI 검색 사실 오류 분석",
        "기업용 AI 검색 솔루션",
        "AI 검색 광고 모델 변화",
    ],
    "AI 사이버보안": [
        "AI 해킹 공격 최신 동향",
        "AI 보안 솔루션 비교",
        "딥페이크 탐지 기술",
        "AI 피싱 이메일 대응",
        "LLM 프롬프트 인젝션 공격",
        "AI로 보안 취약점 찾기",
        "제로데이 AI 탐지",
        "기업 AI 보안 가이드라인",
        "AI 신원 확인 기술",
    ],
    "AI 로보틱스 자율주행": [
        "자율주행 AI 최신 현황",
        "Tesla FSD vs 웨이모 비교",
        "국내 자율주행 현황",
        "AI 로봇 최신 동향 (Figure/Optimus)",
        "물류 로봇 AI 활용",
        "드론 AI 자율 비행",
        "AI 로봇 윤리 문제",
        "자율주행 사고 책임 분석",
    ],
    "AI 제조 스마트팩토리": [
        "스마트팩토리 AI 도입 사례",
        "AI 품질 검사 시스템",
        "예측 유지보수 AI",
        "AI 공급망 최적화",
        "제조업 AI 로봇 도입",
        "디지털 트윈 AI 활용",
        "한국 제조업 AI 현황",
    ],
    "AI 농업 푸드테크": [
        "스마트팜 AI 기술 현황",
        "AI 작물 병충해 탐지",
        "드론 농업 AI 활용",
        "AI 수확량 예측",
        "푸드테크 AI 스타트업",
        "AI 식품 안전 검사",
        "수직농장 AI 자동화",
    ],
    "AI 스타트업 투자": [
        "AI 스타트업 투자 현황 분석",
        "2025 AI 유니콘 기업 정리",
        "AI 투자 트렌드 변화",
        "VC들이 주목하는 AI 분야",
        "AI 스타트업 실패 사례 분석",
        "AI 기업 밸류에이션 분석",
        "국내 AI 스타트업 투자 현황",
    ],
    "AI 일자리 취업": [
        "AI가 대체하는 직업 목록",
        "AI 시대 살아남는 직업",
        "AI 엔지니어 취업 가이드",
        "AI 프롬프트 엔지니어 연봉",
        "AI로 이력서/자소서 작성",
        "AI 면접 준비 전략",
        "AI 관련 자격증 추천",
        "비개발자 AI 전환 방법",
        "AI 프리랜서 수익 창출",
    ],
    "AI 윤리 편향": [
        "AI 편향 사례 총정리",
        "AI 성별/인종 편향 분석",
        "공정한 AI 개발 원칙",
        "AI 편향 탐지 방법",
        "AI 윤리 가이드라인 비교",
        "AI 의사결정 투명성",
        "딥페이크 윤리 문제",
        "AI 감시 사회 우려",
    ],
    "AI 저작권 지적재산": [
        "AI 생성물 저작권 현황",
        "AI 학습 데이터 저작권 분쟁",
        "예술가 vs AI 저작권 소송",
        "AI 특허 출원 현황",
        "AI 콘텐츠 상업 이용 가이드",
        "각국 AI 저작권 법률 비교",
        "AI 음악 저작권 사례",
    ],
    "AI 규제 EU AI Act": [
        "EU AI Act 핵심 내용 정리",
        "AI 규제 각국 비교",
        "기업의 AI 규제 대응 방법",
        "AI 고위험 시스템 분류",
        "미국 AI 행정명령 분석",
        "한국 AI 기본법 현황",
        "AI 규제가 혁신에 미치는 영향",
    ],
    "AI 데이터센터 전력": [
        "AI 데이터센터 전력 소비 현황",
        "AI의 탄소 발자국 분석",
        "에너지 효율 AI 칩 동향",
        "AI와 기후변화 딜레마",
        "원자력 + AI 데이터센터 트렌드",
        "녹색 AI 데이터센터 사례",
        "AI 전력 문제 해결책",
    ],
    "오픈소스 vs 클로즈드 AI": [
        "오픈소스 AI 장단점 분석",
        "오픈소스 AI 보안 위험성",
        "기업이 오픈소스 AI 선택하는 이유",
        "오픈소스 AI 최고 모델 비교",
        "Meta 오픈소스 전략 분석",
        "오픈소스 AI 비즈니스 모델",
        "오픈소스 AI 커뮤니티 현황",
    ],
    "AI 구독 서비스 비교": [
        "AI 구독 서비스 완전 비교",
        "ChatGPT Plus vs Claude Pro vs Gemini Advanced",
        "AI 구독 최고 가성비 분석",
        "무료 AI 서비스 총정리",
        "기업용 AI 구독 비교",
        "AI 구독 취소 방법 정리",
        "AI 구독료 인상 분석",
    ],
    "AI PC 노트북 추천": [
        "AI PC 추천 2025 완전 가이드",
        "AI PC vs 일반 PC 차이",
        "로컬 AI에 최적 GPU 추천",
        "AI 작업 최적 노트북",
        "Apple M4 vs Snapdragon X AI",
        "AI PC 구매 체크리스트",
        "예산별 AI PC 추천",
    ],
    "AI 스마트폰 온디바이스": [
        "AI 스마트폰 비교 2025",
        "갤럭시 AI 기능 완전 가이드",
        "Apple Intelligence 분석",
        "온디바이스 AI 프라이버시",
        "AI 스마트폰 생산성 활용",
        "AI 카메라 기능 비교",
        "AI 통역 기능 활용법",
    ],
    "AI 웨어러블": [
        "AI 웨어러블 기기 비교",
        "AI 스마트워치 건강 분석",
        "AI 이어폰 번역 기능",
        "AI 안경 최신 동향",
        "AI 웨어러블 의료 활용",
        "AI 웨어러블 프라이버시",
    ],
    "한국 AI 정책 NIPA": [
        "한국 AI 정책 현황 총정리",
        "NIPA AI 지원 사업 안내",
        "정부 AI 바우처 활용법",
        "한국 AI 전략 분석",
        "공공 AI 도입 사례",
        "AI 인력 양성 정책",
        "한국 AI 경쟁력 분석",
    ],
    "네이버 CLOVA AI": [
        "네이버 CLOVA AI 서비스 정리",
        "HyperCLOVA X 성능 분석",
        "네이버 AI 검색 변화",
        "클로바 노트 완전 활용",
        "네이버 AI vs 카카오 AI 비교",
        "네이버 AI B2B 솔루션",
        "클로바 더빙 활용법",
    ],
    "카카오 AI": [
        "카카오 AI 서비스 총정리",
        "카나나 AI 모델 분석",
        "카카오톡 AI 기능 활용",
        "카카오 AI 전략 방향",
        "카카오 vs 네이버 AI 비교",
        "카카오 AI B2B 현황",
    ],
    "삼성 AI": [
        "삼성 AI 전략 총정리",
        "갤럭시 AI 기능 완전 가이드",
        "삼성 가우스 AI 분석",
        "삼성 AI 반도체 전략",
        "삼성 B2B AI 솔루션",
        "삼성 vs 애플 AI 비교",
    ],
    "SK AI 투자": [
        "SK AI 투자 현황 분석",
        "SK텔레콤 AI 서비스 정리",
        "SK하이닉스 AI 메모리 전략",
        "에이닷 AI 서비스 활용",
        "SK AI 생태계 분석",
    ],
    "KT AI": [
        "KT AI 서비스 총정리",
        "KT 믿음 AI 분석",
        "통신사 AI 전략 비교",
        "KT AI B2B 솔루션",
        "KT AI 인프라 현황",
    ],
    "국내 AI 스타트업": [
        "한국 AI 스타트업 TOP 30",
        "국내 AI 유니콘 현황",
        "투자 받은 AI 스타트업 분석",
        "AI 스타트업 취업 가이드",
        "국내 AI 스타트업 서비스 비교",
        "성공한 AI 스타트업 사례",
        "AI 스타트업 창업 가이드",
    ],
    "Manus AI 에이전트": [
        "Manus AI 완전 분석",
        "Manus vs Devin 비교",
        "완전 자율 AI 에이전트 현황",
        "Manus 실제 사용 후기",
        "AI 에이전트 한계 분석",
        "자율 AI 에이전트 미래",
    ],
    "AI 논문 연구": [
        "이번 주 AI 논문 TOP 5",
        "ICLR/NeurIPS 최신 논문 정리",
        "AI 논문 읽는 방법",
        "arXiv AI 핵심 논문 해설",
        "AI 연구 트렌드 분석",
        "AI 논문 구현 실습",
        "한국 AI 연구 현황",
    ],
    "AI 규제 정책": [
        "글로벌 AI 규제 동향",
        "AI 규제 찬반 논쟁",
        "AI 안전 연구 현황",
        "AI 의식/감정 논쟁",
        "AI 존재론적 위험 분석",
        "AI 정렬 문제란",
        "슈퍼인텔리전스 대비 전략",
    ],
    "오픈소스 AI 모델": [
        "오픈소스 AI 모델 TOP 10",
        "오픈소스 모델 성능 벤치마크",
        "Apache 라이선스 AI 모델",
        "오픈소스 AI 상업 이용 가이드",
        "오픈소스 AI 커뮤니티 동향",
        "오픈소스 AI 파인튜닝 사례",
    ],
    "Phi Microsoft 소형LLM": [
        "Phi 모델 성능 분석",
        "소형 LLM 완전 비교",
        "Phi 로컬 실행 가이드",
        "SLM vs LLM 선택 기준",
        "엣지 디바이스 AI 모델",
        "Microsoft SLM 전략 분석",
    ],
    "Command R Cohere": [
        "Cohere AI 서비스 정리",
        "Command R+ 분석",
        "기업용 AI에 Cohere 쓰는 이유",
        "RAG 특화 Cohere 활용",
        "Cohere API 실전",
        "Cohere vs OpenAI 기업용 비교",
    ],
    "AI 부동산": [
        "부동산 AI 서비스 현황",
        "AI 집값 예측 정확도",
        "AI 임장 리포트 자동화",
        "부동산 AI 챗봇 활용",
        "건축 설계 AI 도구",
        "AI 인테리어 설계",
    ],
}


# ── 도메인 로테이션 ────────────────────────────────────────────────────────

def get_todays_domains() -> list:
    """날짜 seed 기반 20개 도메인 선택 — 전체 순환 보장"""
    seed = int(hashlib.md5(TODAY.encode()).hexdigest(), 16) % len(AI_DOMAINS)
    rotated = AI_DOMAINS[seed:] + AI_DOMAINS[:seed]
    return rotated[:DAILY_DOMAINS_COUNT]


def load_weekly_angles() -> dict:
    """
    이번 주 동적 앵글 파일 로드.
    없으면 지난 주 파일 시도, 그것도 없으면 정적 TOPIC_SUBTYPES 반환.
    """
    angles_dir = os.path.join(BASE, "output", "angles")

    # 이번 주 → 지난 주 → 2주 전 순서로 탐색
    for delta in [0, 7, 14]:
        target_date = datetime.date.today() - datetime.timedelta(days=delta)
        year_ww = target_date.strftime("%Y-W%V")
        path = os.path.join(angles_dir, f"topic_angles_{year_ww}.json")
        if os.path.exists(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
                angles = data.get("angles", {})
                if angles:
                    print(f"  [앵글] 주간 파일 로드: {path} (총 {data.get('total_angles',0)}개)")
                    return angles
            except Exception as e:
                print(f"  [앵글 ERR] {path}: {e}")

    # 전부 없으면 정적 fallback
    print("  [앵글] 주간 파일 없음 → 정적 TOPIC_SUBTYPES 사용")
    return TOPIC_SUBTYPES


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def http_get(url, headers=None, timeout=12):
    h = {"User-Agent": "Mozilla/5.0 Chrome/120", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def brave_search(query, count=10):
    if not BRAVE_API_KEY:
        return []
    url = (f"https://api.search.brave.com/res/v1/web/search"
           f"?q={urllib.parse.quote(query)}&count={count}&search_lang=ko&freshness=pw")
    try:
        data = http_get(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        })
        results = data.get("web", {}).get("results", [])
        return [{"title": r.get("title",""), "url": r.get("url",""),
                 "snippet": r.get("description","")} for r in results]
    except Exception as e:
        print(f"  [Brave ERR] {e}")
        return []


def fetch_gnews(query, max_results=5):
    """Google News RSS — 최근 1주일 뉴스"""
    try:
        q = urllib.parse.quote(f"{query} when:7d")
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="replace")
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        results = []
        for item in items[:max_results]:
            title = re.search(r"<title>(.*?)</title>", item)
            link  = re.search(r"<link/>(.*?)<", item)
            pub   = re.search(r"<pubDate>(.*?)</pubDate>", item)
            results.append({
                "title":   re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else "",
                "url":     link.group(1).strip() if link else "",
                "pubdate": pub.group(1).strip()  if pub  else "",
            })
        return [r for r in results if r["title"]]
    except Exception as e:
        print(f"  [GNews ERR] {e}")
        return []


def fetch_arxiv(query, max_results=3):
    try:
        q = urllib.parse.quote(query)
        url = (f"https://export.arxiv.org/api/query"
               f"?search_query=all:{q}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            xml = r.read().decode("utf-8", errors="replace")
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        results = []
        for e in entries:
            title   = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            summary = re.search(r"<summary>(.*?)</summary>", e, re.DOTALL)
            link    = re.search(r'href="(https://arxiv\.org/abs/[^"]+)"', e)
            results.append({
                "title":   title.group(1).strip().replace("\n", " ") if title else "",
                "summary": summary.group(1).strip().replace("\n", " ")[:300] if summary else "",
                "url":     link.group(1) if link else "",
            })
        return [r for r in results if r["title"]]
    except Exception as e:
        print(f"  [arXiv ERR] {e}")
        return []


def fetch_arxiv_weekly() -> list:
    """arXiv 최신 AI/ML/NLP 논문 10편 → 쿼리 후보 리스트"""
    try:
        url = ("https://export.arxiv.org/api/query"
               "?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL"
               "&sortBy=submittedDate&sortOrder=descending&max_results=10")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read().decode("utf-8", errors="replace")
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        results = []
        for e in entries:
            title = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            if title:
                t = title.group(1).strip().replace("\n", " ")
                results.append({
                    "query":   t[:80],
                    "domain":  "AI 논문 연구",
                    "source":  "arxiv_weekly",
                    "pubdate": "",
                })
        return results
    except Exception as e:
        print(f"  [arXiv Weekly ERR] {e}")
        return []


def fetch_hackernews(query, max_results=5) -> list:
    """HackerNews Algolia API — 포인트 10 이상 스토리"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = (f"https://hn.algolia.com/api/v1/search"
               f"?query={encoded_query}&tags=story"
               f"&numericFilters=points>10&hitsPerPage={max_results}")
        data = http_get(url)
        hits = data.get("hits", [])
        return [{
            "title":        h.get("title", ""),
            "url":          h.get("url", ""),
            "points":       h.get("points", 0),
            "num_comments": h.get("num_comments", 0),
        } for h in hits if h.get("title")]
    except Exception as e:
        print(f"  [HN ERR] {e}")
        return []


def fetch_reddit_ai(query, max_results=5) -> list:
    """Reddit AI 관련 서브레딧 검색"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = (f"https://www.reddit.com/r/artificial+MachineLearning+LocalLLaMA"
               f"/search.json?q={encoded_query}&sort=hot&limit={max_results}&restrict_sr=1")
        req = urllib.request.Request(url, headers={
            "User-Agent": "research-bot/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        posts = data.get("data", {}).get("children", [])
        return [{
            "title":     p["data"].get("title", ""),
            "url":       p["data"].get("url", ""),
            "score":     p["data"].get("score", 0),
            "subreddit": p["data"].get("subreddit", ""),
        } for p in posts if p.get("data", {}).get("title")]
    except Exception as e:
        print(f"  [Reddit ERR] {e}")
        return []


def fetch_producthunt_ai(max_results=5) -> list:
    """Product Hunt RSS에서 AI 관련 제품 필터"""
    try:
        url = "https://www.producthunt.com/feed"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            xml_bytes = r.read()

        # XML 파싱
        try:
            root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
        except ET.ParseError:
            return []

        items = root.findall(".//item")
        results = []
        for item in items:
            title_el = item.find("title")
            link_el  = item.find("link")
            desc_el  = item.find("description")

            title   = title_el.text.strip() if title_el is not None and title_el.text else ""
            link    = link_el.text.strip()  if link_el  is not None and link_el.text  else ""
            tagline = desc_el.text.strip()  if desc_el  is not None and desc_el.text  else ""

            # AI / GPT / LLM 포함 항목만
            combined = (title + " " + tagline).upper()
            if any(kw in combined for kw in ["AI", "GPT", "LLM"]):
                results.append({"name": title, "url": link, "tagline": tagline})

            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        print(f"  [ProductHunt ERR] {e}")
        return []


def fetch_github_trending():
    try:
        url = ("https://api.github.com/search/repositories"
               "?q=topic:llm+topic:ai+pushed:>2025-01-01&sort=stars&order=desc&per_page=5")
        data = http_get(url, headers={"Accept": "application/vnd.github+json"})
        repos = data.get("items", [])
        return [{"name": r.get("full_name",""), "desc": r.get("description",""),
                 "stars": r.get("stargazers_count", 0), "url": r.get("html_url","")} for r in repos]
    except Exception as e:
        print(f"  [GitHub ERR] {e}")
        return []


# ── 중복 방지 ─────────────────────────────────────────────────────────────────

# 중복 판정 시 핵심 키워드 (3개 이상 겹치면 무조건 중복)
CORE_KEYWORDS = {
    "claude", "chatgpt", "gemini", "gpt", "gpt-4", "gpt-5",
    "ai안전", "ai규제", "openai", "anthropic", "google",
    "llama", "mistral", "deepseek", "perplexity", "copilot",
    "midjourney", "stablediffusion", "sora", "runway",
    "langchain", "llamaindex", "huggingface",
    "transformer", "rlhf", "lora", "gguf",
}


def get_words(text: str) -> set:
    """텍스트에서 단어 집합 추출"""
    return set(re.findall(r"[\w가-힣]+", text.lower()))


def get_bigrams(text: str) -> set:
    """텍스트에서 2-gram 집합 추출"""
    words = re.findall(r"[\w가-힣]+", text.lower())
    if len(words) < 2:
        return set()
    return {(words[i], words[i+1]) for i in range(len(words)-1)}


def similarity_score(a: str, b: str) -> float:
    """단어 기반 + bigram 기반 유사도 (0~1), 두 값의 평균"""
    words_a = get_words(a)
    words_b = get_words(b)
    bigrams_a = get_bigrams(a)
    bigrams_b = get_bigrams(b)

    # 단어 유사도
    if words_a and words_b:
        word_sim = len(words_a & words_b) / len(words_a | words_b)
    else:
        word_sim = 0.0

    # bigram 유사도
    if bigrams_a and bigrams_b:
        bigram_sim = len(bigrams_a & bigrams_b) / len(bigrams_a | bigrams_b)
    else:
        bigram_sim = 0.0

    # 평균
    return (word_sim + bigram_sim) / 2.0


def has_core_keyword_overlap(a: str, b: str, threshold=3) -> bool:
    """핵심 단어가 threshold개 이상 겹치면 True"""
    words_a = get_words(a) & CORE_KEYWORDS
    words_b = get_words(b) & CORE_KEYWORDS
    return len(words_a & words_b) >= threshold


def is_duplicate(candidate: str, history: set, threshold=0.35) -> bool:
    """
    후보 주제가 기존 이력과 유사한지 검사
    - 임계값 0.35 (강화)
    - bigram 포함 유사도
    - 핵심 단어 3개 이상 겹치면 무조건 중복
    """
    cand_lower = candidate.lower()
    for h in history:
        if not h:
            continue
        h_lower = h.lower()
        # 핵심 키워드 3개 이상 겹침 → 무조건 중복
        if has_core_keyword_overlap(cand_lower, h_lower, threshold=3):
            return True
        # 유사도 기반 판단
        if similarity_score(cand_lower, h_lower) >= threshold:
            return True
    return False


def load_posted_history(days=60) -> set:
    """
    최근 N일 포스팅된 키워드/제목 집합 로드
    포함 경로:
      - output/posts/*_meta.json
      - output/topics/daily_topics_*.json
      - p004-blogger/posts/*.md (yaml frontmatter title:)
      - output/published/*.json
    날짜 파싱 실패해도 무조건 포함
    """
    used = set()
    cutoff = datetime.date.today() - datetime.timedelta(days=days)

    # 1) output/posts/ 의 메타 파일 스캔
    if os.path.exists(POSTS):
        for fname in os.listdir(POSTS):
            if not fname.endswith("_meta.json"):
                continue
            try:
                meta = json.load(open(os.path.join(POSTS, fname), encoding="utf-8"))
                for field in ("title", "primary_keyword", "topic"):
                    val = meta.get(field, "").lower()
                    if val:
                        used.add(val)
            except Exception:
                pass

    # 2) output/topics/ 의 daily_topics 스캔
    if os.path.exists(OUTPUT):
        for fname in os.listdir(OUTPUT):
            if not fname.startswith("daily_topics_") or not fname.endswith(".json"):
                continue
            try:
                date_str = fname.replace("daily_topics_", "").replace(".json", "")
                try:
                    fdate = datetime.date.fromisoformat(date_str)
                    if fdate < cutoff or fdate.isoformat() == TODAY:
                        continue
                except Exception:
                    pass  # 날짜 파싱 실패해도 읽기
                data = json.load(open(os.path.join(OUTPUT, fname), encoding="utf-8"))
                for t in data.get("topics", []):
                    for field in ("query", "final_title"):
                        val = t.get(field, "").lower()
                        if val:
                            used.add(val)
            except Exception:
                pass

    # 3) p004-blogger/posts/*.md — yaml frontmatter title: 필드 추출
    blogger_posts_dir = os.path.join(
        BASE, "..", "p004-blogger", "posts"
    )
    blogger_posts_dir = os.path.normpath(blogger_posts_dir)
    if os.path.exists(blogger_posts_dir):
        for fname in os.listdir(blogger_posts_dir):
            if not fname.endswith(".md"):
                continue
            try:
                fpath = os.path.join(blogger_posts_dir, fname)
                with open(fpath, encoding="utf-8", errors="replace") as f:
                    content = f.read(4096)  # frontmatter만 읽으면 충분
                # yaml frontmatter 파싱 (--- ... --- 블록)
                fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if fm_match:
                    fm_text = fm_match.group(1)
                    title_match = re.search(r"^title\s*:\s*['\"]?(.*?)['\"]?\s*$",
                                            fm_text, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip().lower()
                        if title:
                            used.add(title)
            except Exception:
                pass

    # 4) output/published/*.json
    published_dir = os.path.join(BASE, "output", "published")
    if os.path.exists(published_dir):
        for fname in os.listdir(published_dir):
            if not fname.endswith(".json"):
                continue
            try:
                data = json.load(open(os.path.join(published_dir, fname), encoding="utf-8"))
                # 가능한 필드 전부 수집
                for field in ("title", "primary_keyword", "topic", "query", "final_title"):
                    val = data.get(field, "")
                    if isinstance(val, str) and val:
                        used.add(val.lower())
            except Exception:
                pass

    print(f"  [중복방지] 이력 {len(used)}개 로드 (최근 {days}일 + 블로거 포스트 + published)")
    return used


# ── 실시간 트렌드 기반 키워드 생성 ───────────────────────────────────────────

def generate_trending_queries() -> list:
    """
    AI 도메인별 최신 뉴스를 수집해 실제 트렌딩 헤드라인 기반 쿼리 생성
    - 날짜 seed 기반 20개 도메인만 사용 (전체 순환 보장)
    - arXiv 주간 논문도 후보에 추가
    """
    queries = []
    print("  [트렌드 수집] 도메인별 최신 뉴스 기반 쿼리 생성...")

    # 주간 앵글 파일 로드 (한 번만)
    weekly_angles = load_weekly_angles()

    # arXiv 주간 논문 후보 먼저 추가
    arxiv_candidates = fetch_arxiv_weekly()
    queries.extend(arxiv_candidates)
    print(f"  [arXiv Weekly] {len(arxiv_candidates)}개 논문 후보 추가")

    # 오늘의 20개 도메인 (로테이션)
    todays_domains = get_todays_domains()
    print(f"  [도메인 로테이션] 오늘의 도메인 {len(todays_domains)}개: {', '.join(todays_domains[:5])}...")

    for domain in todays_domains:
        news = fetch_gnews(domain, max_results=3)
        if news:
            for n in news[:2]:
                title = n.get("title", "")
                # 언론사 이름 제거 (- 이후)
                title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
                if len(title) > 10:
                    queries.append({
                        "query":   title[:80],
                        "domain":  domain,
                        "source":  "gnews",
                        "pubdate": n.get("pubdate", ""),
                    })

        # ── 세부 토픽 앵글 — 동적 주간 앵글 우선, 없으면 TOPIC_SUBTYPES fallback ──
        # 도메인의 세부 토픽 목록에서 날짜+도메인 seed로 2개 선택
        subtypes = weekly_angles.get(domain, TOPIC_SUBTYPES.get(domain, []))
        if subtypes:
            # seed: 날짜 + 도메인 조합 → 매일 다른 앵글 선택
            seed_str = f"{TODAY}:{domain}"
            sub_seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
            # 세부 토픽 순환 선택 (2개)
            n_sub = len(subtypes)
            idx1 = sub_seed % n_sub
            idx2 = (sub_seed // n_sub + 1) % n_sub
            for idx in [idx1, idx2]:
                subtype = subtypes[idx]
                # "도메인 + 세부앵글" 조합 쿼리
                combined = f"{domain} {subtype}"
                queries.append({
                    "query":   combined[:100],
                    "domain":  domain,
                    "source":  "subtype",
                    "subtype": subtype,
                    "pubdate": "",
                })

        # 도메인 자체도 후보로 추가 (fallback)
        queries.append({"query": domain, "domain": domain, "source": "seed", "pubdate": ""})
        time.sleep(0.3)

    print(f"  [트렌드 수집] {len(queries)}개 쿼리 후보 생성 (뉴스+세부토픽+seed)")
    return queries


def score_candidate(cand: dict, history: set) -> dict:
    """
    후보 쿼리 점수 산출
    - 최신 뉴스 건수 (x3) + 웹 결과 풍부도 + 논문 + HackerNews + Reddit
    - 중복 시 점수 -1 처리
    - 포지셔닝 필드 추가
    """
    query  = cand["query"]
    domain = cand.get("domain", "")

    # 포지셔닝 결정
    positioning = DOMAIN_POSITIONING.get(domain, "트렌드분석")

    # 중복 검사
    if is_duplicate(query, history):
        return {
            **cand,
            "score": -1,
            "duplicate": True,
            "news": [], "web": [], "papers": [],
            "hn": [], "reddit": [],
            "positioning": positioning,
        }

    news   = fetch_gnews(query, max_results=5)
    web    = brave_search(query, count=5)
    papers = fetch_arxiv(re.sub(r"[^\w\s가-힣]", "", query)[:50], max_results=2)
    hn     = fetch_hackernews(query, max_results=5)
    reddit = fetch_reddit_ai(query, max_results=5)

    # 뉴스 신선도
    fresh_news = 0
    today_str = TODAY
    yesterday_str = (datetime.date.today() - datetime.timedelta(1)).isoformat()
    for n in news:
        pd = n.get("pubdate", "")
        if pd and any(x in pd for x in ["today", today_str, yesterday_str]):
            fresh_news += 2
        else:
            fresh_news += 1

    news_score   = fresh_news
    web_score    = len(web)
    paper_score  = len(papers) * 2
    source_bonus = 3 if cand.get("source") == "gnews" else 0
    hn_score     = len(hn) * 2
    reddit_score = len(reddit)

    # subtype 소스 보너스 (세부 앵글 쿼리는 구체적이므로 가산점)
    subtype_bonus = 2 if cand.get("source") == "subtype" else 0
    total = news_score * 3 + web_score + paper_score + source_bonus + hn_score + reddit_score + subtype_bonus

    time.sleep(0.4)
    return {
        **cand,
        "score":        total,
        "duplicate":    False,
        "news":         news,
        "web":          web,
        "papers":       papers,
        "hn":           hn,
        "reddit":       reddit,
        "news_score":   news_score,
        "web_score":    web_score,
        "hn_score":     hn_score,
        "reddit_score": reddit_score,
        "positioning":  positioning,
        "subtype":      cand.get("subtype", ""),
    }


def select_top_topics(n=3) -> list:
    """
    중복 없는 상위 n개 주제 선정 (포지셔닝 다양화)
    1번: 뉴스성 최고점
    2번: 기술심층 또는 산업분석 최고점
    3번: 실용가이드 또는 국내이슈 또는 트렌드분석 최고점
    """
    history = load_posted_history(days=60)

    # 오늘 트렌딩 쿼리 생성
    candidates_raw = generate_trending_queries()

    # 도메인 다양성 확보: 같은 도메인에서 2개 이상 안 뽑음
    domain_seen = {}
    deduped = []
    for c in candidates_raw:
        d = c.get("domain", "")
        if domain_seen.get(d, 0) < 2:
            deduped.append(c)
            domain_seen[d] = domain_seen.get(d, 0) + 1

    print(f"\n  [점수 산출] {len(deduped)}개 후보 평가 중...")
    scored = []
    for cand in deduped:
        result = score_candidate(cand, history)
        if result["score"] > 0:
            scored.append(result)
            pos_label = result.get("positioning", "?")
            print(f"    [{result['score']:3d}점][{pos_label}] {result['query'][:55]}")
        else:
            if result.get("duplicate"):
                print(f"    [중복제외] {result['query'][:60]}")

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: -x["score"])

    # 포지셔닝별 그룹 분리
    groups = {
        "뉴스성":   [],
        "기술심층": [],
        "산업분석": [],
        "실용가이드": [],
        "트렌드분석": [],
        "국내이슈": [],
    }
    for s in scored:
        p = s.get("positioning", "트렌드분석")
        if p in groups:
            groups[p].append(s)

    # 포지셔닝 기반 선정
    selected = []
    used_queries = set()

    def pick_best(group_keys: list) -> dict | None:
        """여러 포지셔닝 그룹 중 최고 점수 후보 반환"""
        best = None
        for key in group_keys:
            for cand in groups.get(key, []):
                if cand["query"] in used_queries:
                    continue
                if best is None or cand["score"] > best["score"]:
                    best = cand
        return best

    # 1번: 뉴스성
    pick1 = pick_best(["뉴스성"])
    if pick1:
        selected.append(pick1)
        used_queries.add(pick1["query"])

    # 2번: 기술심층 or 산업분석
    pick2 = pick_best(["기술심층", "산업분석"])
    if pick2:
        selected.append(pick2)
        used_queries.add(pick2["query"])

    # 3번: 실용가이드 or 국내이슈 or 트렌드분석
    pick3 = pick_best(["실용가이드", "국내이슈", "트렌드분석"])
    if pick3:
        selected.append(pick3)
        used_queries.add(pick3["query"])

    # 부족하면 점수 최고 후보로 fallback
    if len(selected) < n:
        for s in scored:
            if s["query"] not in used_queries:
                selected.append(s)
                used_queries.add(s["query"])
            if len(selected) >= n:
                break

    # 그래도 부족하면 도메인 중복 허용
    if len(selected) < n:
        for s in scored:
            if s not in selected:
                selected.append(s)
            if len(selected) >= n:
                break

    print(f"\n  [최종 선정] {len(selected)}개:")
    for i, t in enumerate(selected, 1):
        print(f"    {i}. [{t['score']}점][{t.get('positioning','?')}][{t['domain']}] {t['query'][:55]}")

    return selected[:n]


def build_topic_package(topic_data: dict) -> dict:
    """상세 자료 수집 + 포지셔닝 + content_angle 포함"""
    query       = topic_data["query"]
    positioning = topic_data.get("positioning", "트렌드분석")

    print(f"  [상세 수집] [{positioning}] {query[:60]}")

    extra_web    = brave_search(f"{query} 완벽 가이드 2025", count=8)
    extra_papers = fetch_arxiv(query[:50], max_results=3)
    github       = fetch_github_trending()
    producthunt  = fetch_producthunt_ai(max_results=5)

    # content_angle 자동 생성
    content_angle = CONTENT_ANGLES.get(positioning, "트렌드 배경 → 데이터 근거 → 시사점 → 미래 예측")

    return {
        "query":         query,
        "domain":        topic_data.get("domain", ""),
        "source":        topic_data.get("source", ""),
        "subtype":       topic_data.get("subtype", ""),   # 세부 앵글
        "score":         topic_data["score"],
        "positioning":   positioning,
        "content_angle": content_angle,
        "news":          topic_data.get("news", []),
        "web":           topic_data.get("web", []) + extra_web,
        "papers":        topic_data.get("papers", []) + extra_papers,
        "hn":            topic_data.get("hn", []),
        "reddit":        topic_data.get("reddit", []),
        "producthunt":   producthunt,
        "github":        github,
        "collected_at":  datetime.datetime.utcnow().isoformat(),
    }


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run():
    print(f"[Research Agent v2] {TODAY} 시작")
    print(f"  도메인 총 {len(AI_DOMAINS)}개, 오늘 로테이션: {DAILY_DOMAINS_COUNT}개")

    output_path = os.path.join(OUTPUT, f"daily_topics_{TODAY}.json")
    if os.path.exists(output_path):
        print(f"  이미 수집된 파일 존재: {output_path}")
        return json.load(open(output_path))

    print("\n[1/2] 트렌드 기반 주제 선정 중...")
    top_topics = select_top_topics(n=3)

    if not top_topics:
        raise RuntimeError("선정된 주제가 없습니다. API 키 또는 네트워크 확인 필요")

    print("\n[2/2] 상세 자료 수집 중...")
    packages = []
    for t in top_topics:
        pkg = build_topic_package(t)
        packages.append(pkg)
        time.sleep(1)

    result = {"date": TODAY, "topics": packages}

    os.makedirs(OUTPUT, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[Research Agent v2] 완료 → {output_path}")
    return result


if __name__ == "__main__":
    run()
