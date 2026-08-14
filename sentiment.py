"""
부정 리뷰 판단 로직 (하이브리드 방식, 비용 최소화).

1단계: 별점 3점 이하 → 바로 부정으로 확정 (AI 호출 없음)
2단계: 별점 4~5점인데 부정 키워드가 포함된 경우에만 AI(Claude Haiku)로 재판단
       → 별점은 높지만 내용이 부정적인 리뷰(예: "시설은 좋은데 직원이 너무 불친절해요")를 잡아내기 위함
3단계: 별점/내용 모두 무난하면 AI 호출 없이 긍정으로 처리

이렇게 하면 병원당 하루 리뷰가 많아도 AI 호출은 소수로 제한됩니다.
"""
import os
import json
from anthropic import Anthropic

NEGATIVE_KEYWORDS = [
    "불친절", "실망", "별로", "환불", "부작용", "컴플레인", "최악", "후회",
    "짜증", "불만", "대기시간이", "대기만", "무성의", "불신", "다시는", "비추", "화가",
    "설명도", "돈만", "사기", "불쾌",
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
    """Claude Haiku로 리뷰 내용의 부정 여부만 판단. True/False 반환."""
    client = _get_client()
    prompt = (
        "다음은 병원 리뷰입니다. 이 리뷰가 병원 입장에서 '부정적인 리뷰'인지 판단해주세요.\n"
        "단순 사실 서술이나 중립적 내용은 부정으로 보지 마세요. "
        "불만, 컴플레인, 재방문 거부 의사, 서비스/의료 품질에 대한 비판이 담긴 경우만 부정으로 판단하세요.\n\n"
        f"리뷰: {content}\n\n"
        '오직 JSON 한 줄로만 답하세요: {"is_negative": true} 또는 {"is_negative": false}'
    )
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )
    try:
        parsed = json.loads(raw_text.strip())
        return bool(parsed.get("is_negative", False))
    except (json.JSONDecodeError, AttributeError):
        # 파싱 실패 시 안전하게 '확인 필요'로 간주 (부정으로 표시해 사람이 보게)
        return True


def judge_review(rating, content: str) -> tuple[bool, str]:
    """
    Returns: (is_negative: bool, 판단근거: str)
    """
    try:
        rating_num = float(rating)
    except (TypeError, ValueError):
        rating_num = None

    if rating_num is not None and rating_num <= 3:
        return True, "별점기준"

    if _rule_flag(content):
        is_neg = _ai_judge(content)
        return is_neg, "AI판단" if is_neg else "AI판단(긍정)"

    return False, "정상"
