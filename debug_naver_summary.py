"""
네이버 플레이스 페이지의 HTML을 그대로 받아와서, 그 안에 리뷰 개수/평균 별점
관련 데이터가 서버에서 미리 렌더링(SSR)되어 있는지 확인하는 스크립트.

캡차에 걸렸던 건 '전체 리뷰 목록'을 요청하는 API 호출이었고, 페이지 자체(HTML)는
정상적으로 200으로 로딩됐었습니다. 이 스크립트는 Selenium 없이 requests만으로
페이지를 받아봅니다 — 이게 성공하면 훨씬 가볍고 안정적인 방식으로 갈 수 있습니다.

사용법:
    python debug_naver_summary.py
"""
import re
import requests

PLACE_ID = "1113270147"
URL = f"https://pcmap.place.naver.com/restaurant/{PLACE_ID}/home"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

print(f"요청: {URL}")
resp = requests.get(URL, headers=HEADERS, timeout=15)
print(f"상태 코드: {resp.status_code}")
print(f"응답 길이: {len(resp.text)} 글자")

html = resp.text

# 원본 HTML을 파일로 저장 (필요하면 직접 열어서 검색해볼 수 있도록)
with open("naver_page_raw.html", "w", encoding="utf-8") as f:
    f.write(html)
print("원본 HTML 저장됨: naver_page_raw.html")

# 별점/리뷰수와 관련되어 보이는 키워드 주변 텍스트를 찾아서 미리보기 출력
keywords = ["avgRating", "visitorReviewsTotal", "reviewCount", "\"rating\"", "totalCount"]
print("\n=== 키워드별 주변 텍스트 미리보기 ===")
for kw in keywords:
    matches = [m.start() for m in re.finditer(re.escape(kw), html)]
    print(f"\n[{kw}] 발견 횟수: {len(matches)}")
    for idx in matches[:3]:  # 너무 많으면 앞 3개만
        snippet = html[max(0, idx - 60): idx + 100]
        print(f"  ...{snippet}...")
