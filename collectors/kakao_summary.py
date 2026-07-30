"""
카카오맵 평점/후기수 조회 (근사치 버전).

카카오맵에는 "전체 누적 평점/후기수"를 딱 알려주는 별도 API가 없는 것으로
확인됐습니다 (meta 엔드포인트는 리뷰 강점 배너용 데이터였음). 대신 이미
검증된 리뷰 목록 API(kakao_reviews.py)에서 가져온 최근 리뷰들의 별점을
그 자리에서 평균 내는 방식으로 근사치를 계산합니다.

주의: 이 "후기수"는 카카오맵에 표시되는 전체 누적 후기수가 아니라,
이 API가 한 번에 반환하는 리뷰 개수(보통 최근 20개 내외) 기준입니다.
"""
from collectors.kakao_reviews import fetch_kakao_reviews


def fetch_kakao_summary(place_id: str) -> dict | None:
    """반환값 예: {"리뷰총개수": 20, "평균별점": 4.15} (최근 리뷰 기준 근사치)."""
    reviews = fetch_kakao_reviews(place_id)
    if not reviews:
        return None

    ratings = [r["별점"] for r in reviews if isinstance(r.get("별점"), (int, float))]
    if not ratings:
        return None

    avg_rating = round(sum(ratings) / len(ratings), 2)
    return {"리뷰총개수": len(reviews), "평균별점": avg_rating}
