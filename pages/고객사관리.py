"""
고객사(병원) 관리 화면. 구글시트를 직접 열지 않고 이 화면에서
고객사 추가/수정/삭제, URL(ID) 등록을 처리합니다.
"""
import re
import streamlit as st
from sheets_schema import ensure_schema, add_client, update_client, delete_client

st.set_page_config(page_title="고객사 관리", layout="wide")
st.title("고객사 리뷰 모니터링 - 고객사 관리")


@st.cache_resource
def _get_client_ws():
    client_ws, _, _ = ensure_schema()
    return client_ws


def _extract_id_from_url(platform: str, raw: str) -> str:
    """사용자가 전체 URL을 붙여넣어도 알아서 ID만 뽑아준다.
    이미 ID만 입력한 경우(숫자만)는 그대로 반환."""
    raw = raw.strip()
    if not raw:
        return ""
    if raw.isdigit():
        return raw

    if platform == "kakao":
        m = re.search(r"place\.map\.kakao\.com/(\d+)", raw)
    elif platform == "naver":
        m = re.search(r"place/(\d+)", raw)
    else:  # google - Place ID는 숫자가 아니라 ChIJ... 형태라 그대로 반환
        return raw

    return m.group(1) if m else raw


client_ws = _get_client_ws()


@st.cache_data(ttl=30)
def _load_clients():
    return client_ws.get_all_records()


tab_list, tab_add = st.tabs(["📋 고객사 목록", "➕ 고객사 추가"])

# ── 목록 + 수정/삭제 ──────────────────────────────────────
with tab_list:
    clients = _load_clients()

    if not clients:
        st.info("등록된 고객사가 없습니다. '고객사 추가' 탭에서 추가해주세요.")
    else:
        for client in clients:
            name = client.get("고객사명", "")
            with st.expander(f"{'🟢' if str(client.get('활성여부')).upper() == 'TRUE' else '⚪'} {name}"):
                with st.form(f"edit_form_{name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_active = st.checkbox(
                            "모니터링 활성화", value=str(client.get("활성여부")).upper() == "TRUE",
                            key=f"active_{name}",
                        )
                        new_google = st.text_input(
                            "구글 Place ID (참고용, 자동수집 안 됨)", value=client.get("구글_PlaceID", ""), key=f"google_{name}"
                        )
                    with col2:
                        new_kakao = st.text_input(
                            "카카오맵 URL 또는 ID", value=client.get("카카오_장소ID", ""), key=f"kakao_{name}"
                        )
                        new_naver = st.text_input(
                            "네이버플레이스 URL 또는 ID", value=client.get("네이버_플레이스ID", ""), key=f"naver_{name}"
                        )

                    save_col, delete_col = st.columns([1, 1])
                    with save_col:
                        submitted = st.form_submit_button("💾 저장", type="primary", use_container_width=True)
                    with delete_col:
                        deleted = st.form_submit_button("🗑️ 삭제", use_container_width=True)

                    if submitted:
                        update_client(
                            client_ws, original_name=name,
                            active=new_active,
                            google_id=new_google,
                            kakao_id=_extract_id_from_url("kakao", new_kakao),
                            naver_id=_extract_id_from_url("naver", new_naver),
                        )
                        st.cache_data.clear()
                        st.success(f"{name} 정보가 저장되었습니다.")
                        st.rerun()

                    if deleted:
                        delete_client(client_ws, name)
                        st.cache_data.clear()
                        st.success(f"{name}가 삭제되었습니다.")
                        st.rerun()

# ── 신규 고객사 추가 ──────────────────────────────────────
with tab_add:
    with st.form("add_client_form"):
        new_name = st.text_input("고객사명 *", placeholder="예: OO정형외과")

        st.caption("아래 3개는 URL을 그대로 붙여넣으셔도 됩니다. 자동으로 ID만 추출합니다.")
        google_input = st.text_input("구글 Place ID (참고용, 자동수집 안 됨)", placeholder="ChIJ...")
        kakao_input = st.text_input("카카오맵 링크 또는 ID", placeholder="https://place.map.kakao.com/12345678")
        naver_input = st.text_input("네이버플레이스 링크 또는 ID", placeholder="https://map.naver.com/p/entry/place/1234567890")

        active_input = st.checkbox("등록 즉시 모니터링 활성화", value=True)

        submitted = st.form_submit_button("➕ 고객사 추가", type="primary")

        if submitted:
            if not new_name.strip():
                st.error("고객사명은 필수입니다.")
            else:
                ok = add_client(
                    client_ws,
                    name=new_name,
                    google_id=_extract_id_from_url("google", google_input),
                    kakao_id=_extract_id_from_url("kakao", kakao_input),
                    naver_id=_extract_id_from_url("naver", naver_input),
                    active=active_input,
                )
                if ok:
                    st.cache_data.clear()
                    st.success(f"'{new_name}' 고객사가 추가되었습니다.")
                    st.rerun()
                else:
                    st.error(f"'{new_name}'은(는) 이미 등록되어 있습니다.")
