"""
리뷰 감지 화면.
담당 부서 필터로 좁혀서, 카카오(부정 리뷰 원문) / 네이버(변동 감지)를
따로따로 보여주고 항목별로 '확인' 버튼을 누르면 상태가 넘어간다.
"""
import streamlit as st
import pandas as pd
from sheets_schema import ensure_schema, TEAMS, open_spreadsheet, REVIEW_SHEET

st.set_page_config(page_title="리뷰 감지", page_icon="⚠️", layout="wide")
st.title("리뷰 감지")


@st.cache_data(ttl=30)
def _load_clients():
    client_ws, _, _ = ensure_schema()
    return client_ws.get_all_records()


@st.cache_data(ttl=30)
def _load_reviews():
    sh = open_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    return ws.get_all_records()


def _mark_checked(review_id: str):
    sh = open_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    all_values = ws.get_all_values()
    header = all_values[0]
    id_col = header.index("리뷰ID")
    status_col = header.index("status")
    for row_idx, row in enumerate(all_values[1:], start=2):
        if row[id_col] == review_id:
            ws.update_cell(row_idx, status_col + 1, "확인됨")
            break
    st.cache_data.clear()


clients = _load_clients()
team_map = {c.get("고객사명", ""): c.get("담당부서", "") for c in clients}

selected_team = st.selectbox("담당 부서", ["전체"] + TEAMS)

reviews = _load_reviews()
for r in reviews:
    r["담당부서"] = team_map.get(r.get("고객사명", ""), "")

if selected_team != "전체":
    reviews = [r for r in reviews if r.get("담당부서") == selected_team]

unconfirmed = [r for r in reviews if r.get("status") == "신규" and str(r.get("is_negative", "")).upper() == "TRUE"]
kakao_items = [r for r in unconfirmed if r.get("플랫폼") == "카카오"]
naver_items = [r for r in unconfirmed if r.get("플랫폼") == "네이버"]

col_kakao, col_naver = st.columns(2)

with col_kakao:
    st.subheader(f"카카오맵 부정리뷰감지 {len(kakao_items)}건")
    if not kakao_items:
        st.caption("확인할 항목이 없습니다.")
    for item in kakao_items:
        with st.container(border=True):
            st.markdown(f"**{item.get('고객사명')}** · ⭐{item.get('별점')} · {item.get('담당부서')}")
            st.write(item.get("리뷰내용", ""))
            if st.button("✅ 확인", key=f"confirm_{item['리뷰ID']}"):
                _mark_checked(item["리뷰ID"])
                st.rerun()

with col_naver:
    st.subheader(f"네이버 변동 {len(naver_items)}건")
    if not naver_items:
        st.caption("확인할 항목이 없습니다.")
    for item in naver_items:
        with st.container(border=True):
            st.markdown(f"**{item.get('고객사명')}** · {item.get('담당부서')}")
            st.write(item.get("리뷰내용", ""))
            if st.button("✅ 확인", key=f"confirm_{item['리뷰ID']}"):
                _mark_checked(item["리뷰ID"])
                st.rerun()
