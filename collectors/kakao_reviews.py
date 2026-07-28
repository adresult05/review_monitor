"""
카카오맵 장소 리뷰 수집.

카카오맵은 공식 리뷰 API를 제공하지 않아, 장소 상세 페이지가 내부적으로
호출하는 리뷰 엔드포인트를 그대로 이용합니다. 아래 URL은 실제 브라우저
개발자도구(Network 탭)로 확인한 요청입니다:

    GET https://place-api.map.kakao.com/places/tab/reviews/kakaomap/{place_id}
        ?order=RECOMMENDED&only_photo_review=false

비공개 엔드포인트이므로 카카오 측 구조가 바뀌면 이 코드도 함께 수정이
필요할 수 있습니다. 응답 구조가 바뀌어 파싱이 실패하면 빈 리스트를 반환하고
로그만 남깁니다 (전체 파이프라인이 죽지 않도록).
"""
import time
import hashlib
import requests

REVIEW_LIST_URL = "https://place-api.map.kakao.com/places/tab/reviews/kakaomap/{place_id}"

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


def fetch_kakao_reviews(place_id: str, order: str = "RECOMMENDED") -> list[dict]:
    """
    order:
      - "RECOMMENDED": 카카오 추천순 (기본값, 최신 리뷰가 항상 맨 위는 아닐 수 있음)
      - "LATEST": 최신순으로 보이는 옵션이 있는지는 실제 응답을 봐야 확정 가능.
        만약 order 파라미터에 LATEST 등 다른 값이 있다면 알려주시면 반영하겠습니다.
    """
    url = REVIEW_LIST_URL.format(place_id=place_id)
    params = {"order": order, "only_photo_review": "false"}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[kakao] place_id={place_id} 요청 실패: {e}")
        return []

    reviews = data.get("reviews", [])
    if not reviews:
        return []

    results = []
    for r in reviews:
        review_id_raw = r.get("review_id")
        content = r.get("contents", "")
        rating = r.get("star_rating")
        author = (r.get("meta", {}).get("owner", {}) or {}).get("nickname", "익명")
        written_at = r.get("registered_at", "")

        raw_key = f"kakao_{review_id_raw}" if review_id_raw else f"kakao|{place_id}|{author}|{content}"
        review_id = "kakao_" + hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16]

        results.append({
            "리뷰ID": review_id,
            "플랫폼": "카카오",
            "별점": rating,
            "리뷰내용": content,
            "작성자": author,
            "작성일": written_at,
        })

    time.sleep(1)  # 서버 부담 완화
    return results
