"""
카카오맵 평균평점/후기수 조회.

place-api.map.kakao.com의 meta 엔드포인트를 쓰는데, 정확한 필드명은
debug_kakao_meta.py 실행 결과로 확정해야 합니다. 지금은 흔히 쓰이는 필드명
후보들을 순서대로 시도하고, 다 실패하면 None을 반환하도록(=화면에서 "-"로
표시) 안전하게 만들어뒀습니다. debug_kakao_meta.py 결과 받으면 정확한
경로로 교체할 예정입니다.
"""
import requests

META_URL = "https://place-api.map.kakao.com/places/reviews/kakaomap/meta/{place_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://place.map.kakao.com",
    "Referer": "https://place.map.kakao.com/",
}

# 흔히 쓰이는 필드명 후보 (debug_kakao_meta.py 결과로 확정되면 교체 예정)
_RATING_KEYS = ["avg_rating", "avgRating", "average", "score"]
_COUNT_KEYS = ["review_count", "reviewCount", "totalCount", "total"]


def _find_key(obj, candidates):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in candidates and isinstance(v, (int, float)):
                return v
        for v in obj.values():
            result = _find_key(v, candidates)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_key(item, candidates)
            if result is not None:
                return result
    return None


def fetch_kakao_summary(place_id: str) -> dict | None:
    """반환값 예: {"리뷰총개수": 20, "평균별점": 4.15}. 실패 시 None."""
    url = META_URL.format(place_id=place_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[kakao-summary] place_id={place_id} 요청 실패: {e}")
        return None

    rating = _find_key(data, _RATING_KEYS)
    count = _find_key(data, _COUNT_KEYS)

    if rating is None or count is None:
        print(f"[kakao-summary] place_id={place_id} - 필드 매칭 실패. "
              f"debug_kakao_meta.py로 정확한 필드명 확인 필요.")
        return None

    return {"리뷰총개수": int(count), "평균별점": float(rating)}
