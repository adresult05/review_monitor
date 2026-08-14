import os
import json
from anthropic import Anthropic

# 업종 상관없이 통용되는 확실한 부정 키워드
# (너무 흔하거나 2글자짜리 애매한 단어는 배제하여 오판 차단)
NEGATIVE_KEYWORDS = [
    "불친절", "최악", "환불", "부작용", "컴플레인", "다시는 안", 
    "돈 아까", "돈아깝", "비추", "화가 나", "불쾌", "사기", "쓰레기",
    "위생", "더러", "별로", "비위생", "불만"
]

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _rule_flag(content: str) -> bool:
    return any(kw in (content or "") for kw in NEGATIVE_KEYWORDS)


def _ai_judge(content: str) -> bool:
    """Claude Haiku로 업종 불문 전체 리뷰의 부정 여부 판단 (기본값: False/긍정)"""
    client = _get_client()
    
    # 병원/식당 등 업종 구분을 없애고 모든 서비스 리뷰에 공통 적용
    prompt = (
        "당신은 고객 리뷰 분석 전문가입니다. 주어진 리뷰가 해당 업체/서비스 입장에서 '명백히 부정적인 리뷰'인지 판단하세요.\n\n"
        "[판단 규칙]\n"
        "- 만족, 칭찬, 추천, 재방문 의사, 기분 좋음 등의 표현이 주를 이루면 무조건 False(긍정)입니다.\n"
        "- 단순 사실 서술이나 칭찬 끝에 덧붙인 소소한 피드백/의견도 False(긍정)입니다.\n"
        "- 서비스, 품질, 위생, 태도 등에 대해 '실질적인 불만/비판/손해'가 주된 내용일 때만 True(부정)입니다.\n\n"
        "[예시]\n"
        "- '대기시간은 좀 있었지만 친절하고 좋았어요' -> False\n"
        "- '시설도 깨끗하고 음식/서비스 다 완벽해요!' -> False\n"
        "- '가격 대비 서비스가 너무 안 좋고 직원 태도 때문에 다시는 안 갑니다' -> True\n\n"
        f"리뷰 내용: \"{content}\"\n\n"
        '다른 설명 없이 오직 JSON 한 줄로만 응답하세요: {"is_negative": true} 또는 {"is_negative": false}'
    )
    
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        
        cleaned_text = raw_text.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned_text)
        
        return bool(parsed.get("is_negative", False))
        
    except Exception as e:
        print(f"[AI Judge Error] {e}")
        # 오류 발생 시 4~5점 리뷰이므로 안전하게 False(긍정) 처리
        return False


def judge_review(rating, content: str) -> tuple[bool, str]:
    """
    Returns: (is_negative: bool, 판단근거: str)
    """
    try:
        rating_num = float(rating)
    except (TypeError, ValueError):
        rating_num = None

    # 1단계: 별점 3점 이하 -> 부정 확정
    if rating_num is not None and rating_num <= 3:
        return True, "별점기준"

    # 2단계: 명확한 부정 키워드가 있을 때만 AI 호출
    if _rule_flag(content):
        is_neg = _ai_judge(content)
        return is_neg, "AI판단(부정)" if is_neg else "AI판단(긍정)"

    # 3단계: 부정 키워드가 없으면 AI 호출 없이 무조건 정상(긍정)
    return False, "정상"
