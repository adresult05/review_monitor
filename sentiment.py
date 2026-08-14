import os
import json
from anthropic import Anthropic

# 긍정 리뷰에서 흔히 쓰이는 "대기", "설명도" 등의 단어를 정제하여 불필요한 AI 호출 최소화
NEGATIVE_KEYWORDS = [
    "불친절", "실망", "별로", "환불", "부작용", "컴플레인", "최악", "후회",
    "짜증", "불만", "무성의", "불신", "다시는", "비추", "화가",
    "돈만", "사기", "불쾌", "대기시간이", "대기만", "설명도 안", "설명없이"
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
        "단순 사실 서술이나 중립적 내용, 칭찬이 포함된 솔직 후기는 부정으로 보지 마세요. "
        "불만, 컴플레인, 재방문 거부 의사, 서비스/의료 품질에 대한 비판이 담긴 경우만 부정으로 판단하세요.\n\n"
        f"리뷰: {content}\n\n"
        '다른 설명 없이 오직 JSON 한 줄로만 답하세요: {"is_negative": true} 또는 {"is_negative": false}'
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
        
        # 마크다운 백틱(```json) 제거 태스크
        cleaned_text = raw_text.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned_text)
        return bool(parsed.get("is_negative", False))
        
    except Exception as e:
        print(f"[AI Judge Error] {e}")
        # API 오류나 파싱 실패 시 4~5점 리뷰이므로 안전하게 False(정상) 처리
        return False


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
        return is_neg, "AI판단(부정)" if is_neg else "AI판단(긍정)"

    return False, "정상"
