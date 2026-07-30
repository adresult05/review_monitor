"""
카카오 리뷰 원문을 그냥 훑어볼 수 있는 화면.
팀 선택 + 고객사 검색으로 좁혀서, 등록된 고객사의 최근 카카오 리뷰를 그대로 본다.
"""
import streamlit as st
from sheets_schema import ensure_schema, TEAMS
from collectors.kakao_reviews import fetch_kakao_reviews

st.set_page_config(page_title="카카오리뷰확인", page_icon="💬", layout="wide")
st.title("카카오리뷰확인")
st.caption("등록된 고객사의 카카오맵 최근 리뷰 원문을 그대로 보여줍니다 (최신순).")


@st.cache_data(ttl=30)
def _load_clients():
    client_ws, _, _ = ensure_schema()
    return client_ws.get_all_records()


@st.cache_data(ttl=180)  # 외부 API 호출이라 3분 캐시
def _get_reviews(kakao_id):
    if not kakao_id:
        return []
    return fetch_kakao_reviews(kakao_id)


col_team, col_search = st.columns([1, 2])
with col_team:
    selected_team = st.selectbox("팀 선택", ["전체"] + TEAMS)
with col_search:
    search_text = st.text_input("고객사 검색", placeholder="고객사명 입력")

clients = _load_clients()
clients_with_kakao = [c for c in clients if str(c.get("카카오_장소ID", "")).strip()]

filtered = clients_with_kakao
if selected_team != "전체":
    filtered = [c for c in filtered if c.get("담당부서") == selected_team]
if search_text.strip():
    filtered = [c for c in filtered if search_text.strip() in c.get("고객사명", "")]

if not filtered:
    st.info("조건에 맞는, 카카오맵이 등록된 고객사가 없습니다.")
else:
    selected_client_name = st.selectbox(
        "고객사 선택", [c.get("고객사명", "") for c in filtered]
    )
    selected_client = next((c for c in filtered if c.get("고객사명") == selected_client_name), None)

    if selected_client:
        kakao_id = str(selected_client.get("카카오_장소ID", "")).strip()
        with st.spinner("리뷰 불러오는 중..."):
            reviews = _get_reviews(kakao_id)

        if not reviews:
            st.info("가져온 리뷰가 없습니다.")
        else:
            st.write(f"최근 리뷰 {len(reviews)}건")
            for r in reviews:
                rating = r.get("별점")
                stars = "⭐" * int(rating) if isinstance(rating, (int, float)) else "(별점 없음)"
                with st.container(border=True):
                    st.markdown(f"**{r.get('작성자', '익명')}** · {stars} · {r.get('작성일', '')}")
                    st.write(r.get("리뷰내용", ""))
