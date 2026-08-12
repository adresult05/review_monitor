"""
매일 아침 GitHub Actions에서 실행되는 메인 스크립트.

플랫폼별 방식이 다릅니다:
  - 카카오: 실제 리뷰 원문을 수집해 신규 리뷰만 별점+AI로 부정 여부 판단
    (place-api.map.kakao.com 엔드포인트, 무료, 실제 테스트로 검증됨)
  - 네이버: 리뷰 원문 API는 캡차로 막혀 있어, 대신 공개 페이지에서 무료로
    가져올 수 있는 리뷰 총개수/평균별점을 '리뷰통계이력' 시트에 날짜별로
    쌓고, 가장 최근 이전 기록과 비교해 "확인 필요" 알림 행을 생성한다.
  - 구글: 자동화하지 않음. 무료 스크래핑은 구글맵이 JS 전용 앱이라 안 되고
    (실제 테스트로 확인됨), 유료 API는 쓰지 않기로 결정. 담당자가 수기로
    확인한다. (고객사설정 시트의 구글_PlaceID 컬럼은 참고용으로만 남겨둠 -
    나중에 마음이 바뀌면 collectors/google_reviews.py, google_summary.py를
    다시 연결하면 됨)

리뷰마스터 시트에 이미 있는 리뷰ID는 건너뛴다 (중복 방지).
"""
import datetime

from sheets_schema import (
    ensure_schema, load_active_clients, load_existing_review_ids,
    append_summary_history, get_latest_summary_entry_before, has_summary_entry_for_today,
)
from collectors.kakao_reviews import fetch_kakao_reviews
from collectors.naver_summary import fetch_naver_summary
from sentiment import judge_review


def _check_summary_platform(history_ws, name, platform_id, platform_label, fetch_fn, today_str):
    """네이버 전용: 요약통계(리뷰수/평균별점)를 이력에 쌓고 변화를 감지해 알림 행을 만든다."""
    summary = fetch_fn(platform_id)
    if summary is None:
        return None

    current_count = summary["리뷰총개수"]
    current_rating = summary["평균별점"]

    if not has_summary_entry_for_today(history_ws, name, platform_label, today_str):
        append_summary_history(history_ws, today_str, name, platform_label, current_count, current_rating)

    prev_entry = get_latest_summary_entry_before(history_ws, name, platform_label, today_str)
    if prev_entry is None:
        return None  # 최초 실행이라 비교 대상 없음 (오늘 기록은 기준값으로 저장됨)

    try:
        prev_count = int(prev_entry["리뷰총개수"])
        prev_date = prev_entry["날짜"]
    except (TypeError, ValueError, KeyError):
        return None

    # 평점은 없을 수 있음 (키워드 리뷰만 쓰는 병원 등) - 있으면 float, 없으면 None
    try:
        prev_rating = float(prev_entry["평균별점"])
    except (TypeError, ValueError):
        prev_rating = None

    count_diff = current_count - prev_count
    if count_diff <= 0:
        return None  # 리뷰 수 변화 없으면 알림 없음

    if current_rating is not None and prev_rating is not None:
        rating_diff = round(current_rating - prev_rating, 2)
        is_negative = rating_diff < 0  # 리뷰가 늘었는데 평균이 떨어졌다면 부정 신호
        trend = "하락" if rating_diff < 0 else "상승" if rating_diff > 0 else "변동없음"
        rating_text = f"평균 별점 {prev_rating}→{current_rating} ({trend})"
    else:
        # 평점 정보 자체가 없는 병원 - 리뷰수 증가만으로 일단 확인 필요로 표시
        is_negative = True
        rating_text = "평점 정보 없음(키워드 리뷰 방식)"

    content = (
        f"[{prev_date} → {today_str}]\n\n"
        f"리뷰 {count_diff}건 증가 (총 {prev_count}→{current_count}건), {rating_text}.\n\n"
        f"내용 확인은 {platform_label}에서 직접 확인 필요."
    )

    review_id = f"{platform_label}_summary_{platform_id}_{today_str}"
    return {
        "리뷰ID": review_id,
        "플랫폼": platform_label,
        "별점": "",
        "리뷰내용": content,
        "작성자": "",
        "작성일": today_str,
        "is_negative": is_negative,
        "판단근거": f"{platform_label} 리뷰수/별점 변화 감지 (원문 미확인)",
    }


def run():
    client_ws, review_ws, history_ws = ensure_schema()
    clients = load_active_clients(client_ws)
    existing_ids = load_existing_review_ids(review_ws)

    now_dt = datetime.datetime.now()
    now = now_dt.strftime("%Y-%m-%d %H:%M")
    today_str = now_dt.strftime("%Y-%m-%d")
    new_rows = []
    summary = {"총수집": 0, "신규": 0, "부정신규": 0}

    for client in clients:
        name = client.get("고객사명", "").strip()
        if not name:
            continue

        # ── 카카오: 리뷰 원문 수집 ──────────────────────────
        kakao_id = str(client.get("카카오_장소ID", "")).strip()
        if kakao_id:
            try:
                collected = fetch_kakao_reviews(kakao_id) or []  # None(요청 실패)도 안전하게 빈 리스트로
            except Exception as e:
                print(f"[{name}] 카카오 리뷰 수집 실패: {e}")
                collected = []

            summary["총수집"] += len(collected)

            for r in collected:
                if r["리뷰ID"] in existing_ids:
                    continue

                is_negative, reason = judge_review(r.get("별점"), r.get("리뷰내용", ""))

                new_rows.append([
                    r["리뷰ID"], name, r["플랫폼"], r.get("별점", ""), r.get("리뷰내용", ""),
                    r.get("작성자", ""), r.get("작성일", ""), now,
                    "TRUE" if is_negative else "FALSE", reason, "신규",
                ])
                existing_ids.add(r["리뷰ID"])
                summary["신규"] += 1
                if is_negative:
                    summary["부정신규"] += 1

        # ── 네이버: 요약통계 비교 (구글은 자동화하지 않음) ──────
        naver_id = str(client.get("네이버_플레이스ID", "")).strip()
        if naver_id:
            try:
                alert = _check_summary_platform(history_ws, name, naver_id, "네이버", fetch_naver_summary, today_str)
            except Exception as e:
                print(f"[{name}] 네이버 통계 확인 실패: {e}")
                alert = None

            if alert and alert["리뷰ID"] not in existing_ids:
                new_rows.append([
                    alert["리뷰ID"], name, alert["플랫폼"], alert["별점"],
                    alert["리뷰내용"], alert["작성자"], alert["작성일"], now,
                    "TRUE" if alert["is_negative"] else "FALSE",
                    alert["판단근거"], "신규",
                ])
                existing_ids.add(alert["리뷰ID"])
                summary["신규"] += 1
                if alert["is_negative"]:
                    summary["부정신규"] += 1

    if new_rows:
        review_ws.append_rows(new_rows, value_input_option="USER_ENTERED")

    print(f"[{now}] 완료 - {summary}")
    return summary


if __name__ == "__main__":
    run()
