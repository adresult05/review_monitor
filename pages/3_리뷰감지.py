"""
리뷰 감지 화면.
담당 부서 필터로 좁혀서, 카카오(부정 리뷰 원문) / 네이버(변동 감지)를
따로따로 보여준다.

확인 처리는 3단계로 할 수 있다:
  1. 항목 하나씩 확인
  2. 고객사별로 한 번에 확인 (그 고객사의 미확인 항목 전부)
  3. 전체 확인 (현재 화면에 보이는 모든 미확인 항목)
"""
import time
import streamlit as st
import pandas as pd
import gspread
from sheets_schema import ensure_schema, TEAMS, open_spreadsheet, REVIEW_SHEET, normalize_for_search
from style import inject_css, page_header

inject_css()
page_header("리뷰 감지")


@st.cache_resource
def _get_spreadsheet():
    """구글시트 접속을 세션 안에서 재사용 (버튼 누를 때마다 매번 새로 인증하지 않도록)."""
    return open_spreadsheet()


def _with_retry(func, *args, retries=3, delay=2, **kwargs):
    """구글시트 API가 일시적으로 바쁠 때(429/503 등) 잠깐 기다렸다가 재시도."""
    last_error = None
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            last_error = e
            time.sleep(delay * (attempt + 1))  # 점점 더 길게 대기
    raise last_error


@st.cache_data(ttl=30)
def _load_clients():
    client_ws, _, _ = ensure_schema()
    return _with_retry(client_ws.get_all_records)


@st.cache_data(ttl=30)
def _load_reviews():
    sh = _get_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    return _with_retry(ws.get_all_records)


def _mark_checked_bulk(review_ids: list):
    """여러 리뷰ID를 한 번에 '확인됨'으로 일괄 처리."""
    if not review_ids:
        return
    sh = _get_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    all_values = _with_retry(ws.get_all_values)
    header = all_values[0]
    id_col = header.index("리뷰ID")
    status_col = header.index("status")

    id_set = set(review_ids)
    updates = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        if row[id_col] in id_set:
            updates.append({
                "range": f"{chr(65 + status_col)}{row_idx}",
                "values": [["확인됨"]],
            })
    if updates:
        try:
            _with_retry(ws.batch_update, updates)
        except gspread.exceptions.APIError:
            st.error("구글시트가 일시적으로 응답하지 않아요. 잠시 후 다시 시도해주세요.")
            return
    st.cache_data.clear()


clients = _load_clients()
team_map = {c.get("고객사명", ""): c.get("담당부서", "") for c in clients}
manager_map = {c.get("고객사명", ""): c.get("담당자", "") for c in clients}
kakao_id_map = {c.get("고객사명", ""): str(c.get("카카오_장소ID", "")).strip() for c in clients}
naver_id_map = {c.get("고객사명", ""): str(c.get("네이버_플레이스ID", "")).strip() for c in clients}

col_team, col_search = st.columns([1, 2])
with col_team:
    selected_team = st.selectbox("담당 부서", ["전체"] + TEAMS)
with col_search:
    search_text = st.text_input("고객사 / 담당자 검색", placeholder="고객사명 또는 담당자 이름 입력")

reviews = _load_reviews()
for r in reviews:
    r["담당부서"] = team_map.get(r.get("고객사명", ""), "")
    r["담당자"] = manager_map.get(r.get("고객사명", ""), "")

if selected_team != "전체":
    reviews = [r for r in reviews if r.get("담당부서") == selected_team]
if search_text.strip():
    q = normalize_for_search(search_text)
    reviews = [
        r for r in reviews
        if q in normalize_for_search(r.get("고객사명", "")) or q in normalize_for_search(r.get("담당자", ""))
    ]

unconfirmed = [r for r in reviews if r.get("status") == "신규" and str(r.get("is_negative", "")).upper() == "TRUE"]

# ── 리뷰 파일로 다운로드 (현재 팀 필터 기준, 확인/미확인 전부) ──
if reviews:
    export_df = pd.DataFrame(reviews)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")  # 엑셀에서 한글 안 깨지게
    st.download_button(
        "⬇️ 현재 목록 엑셀(CSV)로 다운로드",
        data=csv_bytes,
        file_name=f"리뷰내역_{selected_team}.csv",
        mime="text/csv",
    )

# ── 전체 확인 버튼 (현재 화면에 보이는 전부) ──────────────
col_title, col_all_confirm = st.columns([4, 1])
with col_title:
    st.caption(f"현재 화면 기준 미확인 {len(unconfirmed)}건")
with col_all_confirm:
    if unconfirmed and st.button("✅ 전체 확인", use_container_width=True):
        _mark_checked_bulk([r["리뷰ID"] for r in unconfirmed])
        st.rerun()

kakao_items = [r for r in unconfirmed if r.get("플랫폼") == "카카오"]
naver_items = [r for r in unconfirmed if r.get("플랫폼") == "네이버"]


def _render_platform_column(title: str, items: list, link_map: dict = None, link_label: str = ""):
    st.subheader(f"{title} {len(items)}건")
    if not items:
        st.caption("확인할 항목이 없습니다.")
        return

    # 고객사별로 묶기
    by_client = {}
    for item in items:
        by_client.setdefault(item.get("고객사명", ""), []).append(item)

    for client_name, client_items in by_client.items():
        header_col, btn_col = st.columns([3, 1])
        with header_col:
            st.markdown(f"**{client_name}** ({len(client_items)}건)")
            if link_map:
                url = link_map.get(client_name, "")
                if url:
                    st.markdown(f"[{link_label}]({url})")
        with btn_col:
            if st.button(f"이 고객사 확인", key=f"client_confirm_{title}_{client_name}"):
                _mark_checked_bulk([it["리뷰ID"] for it in client_items])
                st.rerun()

        for item in client_items:
            with st.container(border=True):
                if title == "카카오맵 부정리뷰감지":
                    st.markdown(f"⭐{item.get('별점')} · {item.get('작성일', '작성일 정보 없음')}")
                st.write(item.get("리뷰내용", ""))
                if st.button("✅ 확인", key=f"confirm_{item['리뷰ID']}"):
                    _mark_checked_bulk([item["리뷰ID"]])
                    st.rerun()
        st.divider()


kakao_links = {name: f"https://place.map.kakao.com/{pid}" for name, pid in kakao_id_map.items() if pid}
naver_links = {name: f"https://map.naver.com/p/entry/place/{pid}" for name, pid in naver_id_map.items() if pid}

col_kakao, col_naver = st.columns(2)
with col_kakao:
    _render_platform_column("카카오맵 부정리뷰감지", kakao_items, link_map=kakao_links, link_label="📍 카카오맵 바로가기")
with col_naver:
    _render_platform_column("네이버 변동", naver_items, link_map=naver_links, link_label="📍 네이버플레이스 바로가기")
