"""
부정 리뷰 판단 로직.

1단계: 별점 3점 이하 → 바로 부정으로 확정 (AI 호출 없음)
2단계: 별점 4~5점(또는 별점 없음)이면서 리뷰 내용이 있는 경우 → AI(Claude Haiku)가 판단
3단계: 리뷰 내용이 아예 없으면 → AI 호출 없이 정상 처리

프롬프트 설계 주의사항 (실제 운영에서 겪은 문제):
  이전 버전은 "어조가 미묘하게 부정적이거나 '애매하면' 부정으로 판단하라"고 했는데,
  이 표현이 너무 광범위해서 "좋아요", "다음에 또 올게요" 같은 명백한 긍정 리뷰까지
  전부 부정으로 판단되는 문제가 있었다. 그래서 아래처럼 바꿨다:
    - 기본값은 '긍정'이고, 명확한 불만 신호가 있을 때만 부정으로 판단하도록 지시
    - 부정으로 볼 구체적 조건과, 부정으로 보면 안 되는 예시를 명시
    - 애매하면 긍정으로 처리하도록 명시 (담당자 확인 부담을 늘리지 않기 위함)
"""
import os
import re
import json
from anthropic import Anthropic

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _extract_json(raw_text: str):
    """AI 응답에서 JSON 객체 부분만 정규식으로 추출해서 파싱. 실패하면 None."""
    if not raw_text:
        return None
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    candidate = match.group(0) if match else cleaned
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _call_ai(content: str):
    client = _get_client()
    prompt = (
        "당신은 병원 리뷰를 검토해서, 병원 담당자가 직접 확인해야 할 '부정적인 리뷰'만 골라내는 역할입니다.\n\n"
        "기본 전제: 대부분의 리뷰는 긍정적입니다. 확실한 불만 신호가 없으면 긍정으로 판단하세요.\n\n"
        "다음 중 하나라도 해당될 때만 부정(true)으로 판단하세요:\n"
        "- 서비스, 의료 품질, 직원 응대 등에 대한 구체적인 불만이나 비판이 있음\n"
        "- 재방문하지 않겠다는 의사를 밝힘\n"
        "- 기대에 못 미쳤다는 실망감을 표현함\n"
        "- 다른 사람에게 추천하지 않겠다는 뜻을 내비침\n\n"
        "다음은 부정이 아닙니다 (false로 판단하세요):\n"
        "- 짧은 칭찬 (예: '좋아요', '친절해요', '만족합니다')\n"
        "- 재방문 의사를 밝힌 리뷰 (예: '다음에 또 올게요')\n"
        "- 단순 사실 서술이나 감상 (예: '여기 새로 생겼네요', '동네에 이런 곳이 생기다니 놀랍네요')\n"
        "- 이모티콘이나 감탄사 위주의 가벼운 리뷰\n"
        "- 판단이 애매한 경우 → 긍정(false)으로 처리하세요\n\n"
        f"리뷰: {content}\n\n"
        '다른 설명 없이 오직 JSON 한 줄로만 답하세요: {"is_negative": true} 또는 {"is_negative": false}'
    )
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )
    return _extract_json(raw_text)


def _ai_judge(content: str) -> bool:
    """Claude Haiku로 리뷰 내용의 부정 여부를 판단. True/False 반환."""
    for attempt in range(2):  # 파싱 실패 시 한 번 더 재시도
        try:
            parsed = _call_ai(content)
        except Exception as e:
            print(f"[sentiment] AI 호출 자체 실패 (시도 {attempt + 1}): {e}")
            parsed = None

        if parsed is not None and "is_negative" in parsed:
            return bool(parsed["is_negative"])

    # 재시도까지 실패하면 '정상'으로 처리 (파싱 실패는 판단 문제가 아니라 형식 문제이므로,
    # 무조건 부정 처리해서 불필요한 확인 작업을 늘리지 않음)
    print(f"[sentiment] JSON 파싱 2번 다 실패, '정상'으로 처리: {content[:50]}")
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

    if not content or not content.strip():
        return False, "정상(내용없음)"

    is_neg = _ai_judge(content)
    return is_neg, "AI판단" if is_neg else "AI판단(긍정)"
