"""
리뷰 모니터링 앱의 메인 화면.
- 접속 시 확인 안 된 부정 리뷰가 있으면 경고 모달이 뜬다
- 아래는 전체 리뷰 현황을 간단히 훑어볼 수 있는 표
"""
import streamlit as st
import pandas as pd
from sheets_schema import open_spreadsheet, REVIEW_SHEET
from streamlit_alert import show_negative_review_alert

st.set_page_config(page_title="리뷰 모니터링", page_icon="⚠️", layout="wide")

# 접속하자마자 부정 리뷰 경고 모달 체크
show_negative_review_alert()

st.title("고객사 리뷰 모니터링")
st.caption("카카오맵 원문 수집 + 네이버 리뷰수/별점 변화 추적 (구글은 수기 확인)")


@st.cache_data(ttl=30)
def _load_reviews():
    sh = open_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    records = ws.get_all_records()
    return pd.DataFrame(records)


df = _load_reviews()

if df.empty:
    st.info("아직 수집된 리뷰가 없습니다. 왼쪽 사이드바에서 '고객사관리'로 이동해 고객사를 먼저 등록해주세요.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("전체 항목", len(df))
    col2.metric("미확인 부정 리뷰", len(df[(df["status"] == "신규") & (df["is_negative"].astype(str).str.upper() == "TRUE")]))
    col3.metric("확인 완료", len(df[df["status"] == "확인됨"]))

    st.divider()

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        client_options = ["전체"] + sorted(df["고객사명"].unique().tolist())
        selected_client = st.selectbox("고객사 필터", client_options)
    with col_filter2:
        platform_options = ["전체"] + sorted(df["플랫폼"].unique().tolist())
        selected_platform = st.selectbox("플랫폼 필터", platform_options)

    filtered = df.copy()
    if selected_client != "전체":
        filtered = filtered[filtered["고객사명"] == selected_client]
    if selected_platform != "전체":
        filtered = filtered[filtered["플랫폼"] == selected_platform]

    st.dataframe(
        filtered.sort_values("수집일시", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
