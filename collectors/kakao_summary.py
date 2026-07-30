"""
카카오맵 평점/후기수 조회 (별점 리뷰 기준 정확한 통계).

실제 테스트로 확인된 panel3 엔드포인트를 사용합니다:
    GET https://place-api.map.kakao.com/places/panel3/{place_id}
    → kakaomap_review.score_set.review_count (별점 리뷰 개수)
    → kakaomap_review.score_set.average_score (평균 별점)

주의: 이 숫자는 '별점을 매긴 리뷰'만 카운트합니다. 카카오맵 앱 화면에 보이는
"리뷰262" 같은 숫자는 별점리뷰+댓글+사진리뷰+블로그리뷰를 합친 숫자라서,
여기서 나오는 값과는 다를 수 있습니다 (저희 목적엔 별점 리뷰 기준이 더 맞습니다).
"""
import requests

PANEL_URL = "https://place-api.map.kakao.com/places/panel3/{place_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://place.map.kakao.com",
    "Referer": "https://place.map.kakao.com/",
    "Appversion": "6.6.0",
    "Pf": "PC",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}


def fetch_kakao_summary(place_id: str) -> dict | None:
    """반환값 예: {"리뷰총개수": 4, "평균별점": 2.0}. 실패 시 None."""
    url = PANEL_URL.format(place_id=place_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[kakao-summary] place_id={place_id} 요청 실패: {e}")
        return None

    try:
        score_set = data["kakaomap_review"]["score_set"]
        review_count = score_set["review_count"]
        average_score = score_set["average_score"]
    except (KeyError, TypeError):
        print(f"[kakao-summary] place_id={place_id} - 응답 구조 변경 가능성")
        return None

    return {"리뷰총개수": review_count, "평균별점": average_score}
