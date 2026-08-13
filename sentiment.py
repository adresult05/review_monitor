"""
부정 리뷰 판단 로직.

1단계: 별점 3점 이하 → 바로 부정으로 확정 (AI 호출 없음)
2단계: 별점 4~5점(또는 별점 없음)이면서 리뷰 내용이 있는 경우 → 무조건 AI(Claude Haiku)가
       내용을 읽고 뉘앙스까지 판단 (키워드 매칭이 아니라 실제 어조/맥락을 이해해서 판단하므로,
       "다음엔 다른 곳도 가볼까 고민 중이에요" 처럼 특정 부정 단어 없이도 은근히 부정적인
       리뷰를 잡아낼 수 있음)
3단계: 리뷰 내용이 아예 없으면 → AI 호출 없이 정상 처리 (판단할 내용 자체가 없으므로)

이전 버전은 부정 키워드가 포함된 경우에만 AI를 호출했지만, 키워드에 없는 표현의 뉘앙스를
놓치는 문제가 있어 제거했습니다. Claude Haiku 자체가 호출당 비용이 매우 낮아, 별점
4~5점 리뷰를 전부 AI로 검토해도 비용 부담은 크지 않습니다.
"""
import os
import json
from anthropic import Anthropic

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _ai_judge(content: str) -> bool:
    """Claude Haiku로 리뷰 내용의 부정 여부(뉘앙스 포함)를 판단. True/False 반환."""
    client = _get_client()
    prompt = (
        "다음은 병원 리뷰입니다. 이 리뷰가 병원 입장에서 '부정적인 리뷰'인지 판단해주세요.\n"
        "특정 부정 단어가 없어도, 전체적인 어조나 뉘앙스가 미묘하게 부정적이거나 애매하면"
        "(예: 재방문 의사가 불확실하거나, 기대에 못 미쳤다는 느낌 등) 부정으로 판단하세요.\n"
        "단순 사실 서술이나 명확히 긍정적인 내용은 부정으로 보지 마세요.\n\n"
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
    except Exception:
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

    if not content or not content.strip():
        return False, "정상(내용없음)"

    is_neg = _ai_judge(content)
    return is_neg, "AI판단" if is_neg else "AI판단(긍정)"
