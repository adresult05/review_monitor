"""
Google Places API (New)로 특정 Place의 리뷰를 가져옵니다.
공식 API라 가장 안정적이지만, 장소당 최대 5개 리뷰만 반환되고
정렬은 '관련도순'입니다 (최신순 아님).

사전 준비:
  - GCP 콘솔에서 "Places API (New)" 활성화
  - API 키 발급 후 환경변수 GOOGLE_PLACES_API_KEY 에 저장
"""
import os
import requests
import hashlib

PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"


def fetch_google_reviews(place_id: str) -> list[dict]:
    api_key = os.environ["GOOGLE_PLACES_API_KEY"]
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "reviews",
    }
    url = PLACE_DETAILS_URL.format(place_id=place_id)
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for r in data.get("reviews", []):
        text = (r.get("text", {}) or {}).get("text", "")
        author = (r.get("authorAttribution", {}) or {}).get("displayName", "익명")
        rating = r.get("rating")
        publish_time = r.get("publishTime", "")

        # 원본에 고유 ID가 없으므로 place_id+author+text 해시로 리뷰ID 생성
        raw_key = f"google|{place_id}|{author}|{text}"
        review_id = "google_" + hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16]

        results.append({
            "리뷰ID": review_id,
            "플랫폼": "구글",
            "별점": rating,
            "리뷰내용": text,
            "작성자": author,
            "작성일": publish_time,
        })
    return results
