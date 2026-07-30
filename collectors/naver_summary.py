"""
네이버 플레이스 리뷰 '요약 통계' 수집기 (안정 버전).

리뷰 원문 목록은 캡차에 막히지만, 페이지 HTML 자체에는 서버에서 미리 렌더링된
리뷰 총 개수(visitorReviewsTotal)와 평균 별점(avgRating)이 포함되어 있습니다.
이 값은 Selenium/로그인 없이 requests만으로 안정적으로 가져올 수 있습니다.

접근 방식이 달라짐:
  - 리뷰 "내용"까지는 못 가져옵니다 (캡차 때문에).
  - 대신 "어제 대비 리뷰 수가 몇 개 늘었는지 / 평균 별점이 떨어졌는지"를 추적합니다.
  - 리뷰 수가 늘었는데 평균 별점이 같이 떨어졌다면 "새로 달린 리뷰들의 평균이
    기존보다 낮다"는 뜻이므로 부정 리뷰 가능성 신호로 판단합니다.
  - 정확히 몇 번째 리뷰가 부정적인지는 알 수 없으므로, 알림에는 "이 병원 리뷰
    수/별점이 이렇게 변했으니 스마트플레이스에서 직접 확인해보세요"라는 형태로
    안내합니다.

주의:
  - businessType에 따라 URL 경로가 다를 수 있습니다 (예: /restaurant/, /hospital/
    등). 병원 페이지에서 실제 URL 경로를 확인해서 아래 PATH_CANDIDATES에 맞춰
    시도합니다.
"""
import re
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 업종에 따라 naver map URL 경로가 다를 수 있어 순서대로 시도
PATH_CANDIDATES = ["restaurant", "hospital", "place"]


def fetch_naver_summary(place_id: str) -> dict | None:
    """
    반환값 예:
        {"리뷰총개수": 863, "평균별점": 4.08}
    실패 시 None
    """
    for path in PATH_CANDIDATES:
        url = f"https://pcmap.place.naver.com/{path}/{place_id}/home"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            print(f"[naver-summary] place_id={place_id} path={path} 요청 실패: {e}")
            continue

        if resp.status_code != 200:
            continue

        html = resp.text

        # avgRating과 totalCount가 함께 나오는 지점을 정규식으로 추출
        match = re.search(
            r'"avgRating":([\d.]+),"totalCount":(\d+)', html
        )
        if match:
            avg_rating = float(match.group(1))
            total_count = int(match.group(2))
            return {"리뷰총개수": total_count, "평균별점": avg_rating}

        # 위 패턴이 안 맞으면 visitorReviewsTotal / visitorReviewsScore로 재시도
        total_match = re.search(r'"visitorReviewsTotal":(\d+)', html)
        score_match = re.search(r'"visitorReviewsScore":([\d.]+)', html)
        if total_match and score_match:
            return {
                "리뷰총개수": int(total_match.group(1)),
                "평균별점": float(score_match.group(1)),
            }

    print(f"[naver-summary] place_id={place_id} - 모든 경로에서 데이터 추출 실패")
    return None
