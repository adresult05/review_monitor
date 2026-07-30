"""
모니터링 현황 화면.
팀 선택 + 고객사 검색으로, 고객사별 모니터링 on/off 상태와
플랫폼별(카카오/네이버) 등록 여부, 평점/후기수를 한눈에 본다.

주의: 카카오/네이버 평점·후기수는 그 자리에서 실시간으로 가져오기 때문에,
고객사 수가 많으면 로딩에 몇 초 걸릴 수 있다. (세션 내 5분 캐시)
"""
import streamlit as st
import pandas as pd
from sheets_schema import ensure_schema, TEAMS
from collectors.kakao_summary import fetch_kakao_summary
from collectors.naver_summary import fetch_naver_summary

st.set_page_config(page_title="모니터링 현황", page_icon="📡", layout="wide")
st.title("모니터링 현황")


@st.cache_data(ttl=30)
def _load_clients():
    client_ws, _, _ = ensure_schema()
    return client_ws.get_all_records()


@st.cache_data(ttl=300)  # 외부 API 호출이라 5분 캐시
def _get_kakao_stat(kakao_id):
    if not kakao_id:
        return None
    return fetch_kakao_summary(kakao_id)


@st.cache_data(ttl=300)
def _get_naver_stat(naver_id):
    if not naver_id:
        return None
    return fetch_naver_summary(naver_id)


col_team, col_search = st.columns([1, 2])
with col_team:
    selected_team = st.selectbox("팀 선택", ["전체"] + TEAMS)
with col_search:
    search_text = st.text_input("고객사 검색", placeholder="고객사명 입력")

clients = _load_clients()

if not clients:
    st.info("등록된 고객사가 없습니다.")
else:
    filtered = clients
    if selected_team != "전체":
        filtered = [c for c in filtered if c.get("담당부서") == selected_team]
    if search_text.strip():
        filtered = [c for c in filtered if search_text.strip() in c.get("고객사명", "")]

    if not filtered:
        st.info("조건에 맞는 고객사가 없습니다.")
    else:
        rows = []
        with st.spinner("평점/후기수 불러오는 중..."):
            for c in filtered:
                kakao_id = str(c.get("카카오_장소ID", "")).strip()
                naver_id = str(c.get("네이버_플레이스ID", "")).strip()
                is_active = str(c.get("활성여부", "")).strip().upper() == "TRUE"

                kakao_stat = _get_kakao_stat(kakao_id) if kakao_id else None
                naver_stat = _get_naver_stat(naver_id) if naver_id else None

                rows.append({
                    "모니터링": "🔵 ON" if is_active else "⚪ OFF",
                    "고객사명": c.get("고객사명", ""),
                    "담당부서": c.get("담당부서", ""),
                    "카카오": "🟡 등록" if kakao_id else "⚫ 미등록",
                    "카카오평점": kakao_stat["평균별점"] if kakao_stat else "-",
                    "카카오후기수": kakao_stat["리뷰총개수"] if kakao_stat else "-",
                    "네이버": "🟢 등록" if naver_id else "⚫ 미등록",
                    "네이버평점": naver_stat["평균별점"] if naver_stat else "-",
                    "네이버후기수": naver_stat["리뷰총개수"] if naver_stat else "-",
                })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
