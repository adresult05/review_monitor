"""
고객사(병원) 등록/수정/삭제 화면. 담당 부서 배정도 여기서 처리.
목록 탭에는 모니터링현황처럼 팀 선택 + 고객사 검색 필터가 있다.
"""
import re
import pandas as pd
import streamlit as st
from sheets_schema import ensure_schema, add_client, update_client, delete_client, TEAMS
from style import inject_css, page_header

inject_css()
page_header("고객사")


@st.cache_resource
def _get_client_ws():
    client_ws, _, _ = ensure_schema()
    return client_ws


def _extract_id_from_url(platform: str, raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.isdigit():
        return raw
    if platform == "kakao":
        m = re.search(r"place\.map\.kakao\.com/(\d+)", raw)
    elif platform == "naver":
        m = re.search(r"place/(\d+)", raw)
    else:
        return raw
    return m.group(1) if m else raw


client_ws = _get_client_ws()


@st.cache_data(ttl=30)
def _load_clients():
    return client_ws.get_all_records()


tab_list, tab_add, tab_bulk = st.tabs(["📋 고객사 목록", "➕ 고객사 추가", "📥 일괄 등록"])

with tab_list:
    clients = _load_clients()

    if not clients:
        st.info("등록된 고객사가 없습니다. '고객사 추가' 탭에서 추가해주세요.")
    else:
        col_team, col_search = st.columns([1, 2])
        with col_team:
            selected_team = st.selectbox("팀 선택", ["전체"] + TEAMS, key="client_page_team_filter")
        with col_search:
            search_text = st.text_input("고객사 검색", placeholder="고객사명 입력", key="client_page_search")

        filtered = clients
        if selected_team != "전체":
            filtered = [c for c in filtered if c.get("담당부서") == selected_team]
        if search_text.strip():
            filtered = [c for c in filtered if search_text.strip() in c.get("고객사명", "")]

        if not filtered:
            st.info("조건에 맞는 고객사가 없습니다.")

        for client in filtered:
            name = client.get("고객사명", "")
            team_label = client.get("담당부서", "") or "미배정"
            with st.expander(f"{'🟢' if str(client.get('활성여부')).upper() == 'TRUE' else '⚪'} {name} · {team_label}"):
                with st.form(f"edit_form_{name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_active = st.checkbox(
                            "모니터링 활성화", value=str(client.get("활성여부")).upper() == "TRUE",
                            key=f"active_{name}",
                        )
                        current_team = client.get("담당부서", "")
                        team_index = TEAMS.index(current_team) if current_team in TEAMS else 0
                        new_team = st.selectbox("담당 부서", TEAMS, index=team_index, key=f"team_{name}")
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
                            kakao_id=_extract_id_from_url("kakao", new_kakao),
                            naver_id=_extract_id_from_url("naver", new_naver),
                            team=new_team,
                        )
                        st.cache_data.clear()
                        st.toast(f"{name} 정보가 저장되었습니다.", icon="✅")
                        st.rerun()

                    if deleted:
                        delete_client(client_ws, name)
                        st.cache_data.clear()
                        st.toast(f"{name}가 삭제되었습니다.", icon="🗑️")
                        st.rerun()

with tab_add:
    with st.form("add_client_form"):
        new_name = st.text_input("고객사명 *", placeholder="예: OO정형외과")
        new_team = st.selectbox("담당 부서 *", TEAMS)

        st.caption("아래 2개는 URL을 그대로 붙여넣으셔도 됩니다. 자동으로 ID만 추출합니다.")
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
                    kakao_id=_extract_id_from_url("kakao", kakao_input),
                    naver_id=_extract_id_from_url("naver", naver_input),
                    active=active_input,
                    team=new_team,
                )
                if ok:
                    st.cache_data.clear()
                    st.toast("고객사 등록이 완료되었습니다!", icon="✅")
                    st.rerun()
                else:
                    st.error(f"'{new_name}'은(는) 이미 등록되어 있습니다.")

with tab_bulk:
    st.write("**방법 1. 엑셀에서 표를 복사해서 아래 표에 붙여넣기**")
    st.caption("엑셀에서 고객사명/담당부서/카카오ID(또는 링크)/네이버ID(또는 링크) 순서로 열을 만들어 복사한 뒤, "
               "아래 표의 첫 칸을 클릭하고 Ctrl+V로 붙여넣으세요. 담당부서는 정확히 다음 중 하나여야 합니다: "
               + ", ".join(TEAMS))

    template_df = pd.DataFrame(
        [{"고객사명": "", "담당부서": "", "카카오ID_또는_URL": "", "네이버ID_또는_URL": ""} for _ in range(5)]
    )
    edited_df = st.data_editor(
        template_df, num_rows="dynamic", use_container_width=True, key="bulk_editor",
    )

    if st.button("📥 표에 입력한 내용으로 일괄 등록", type="primary"):
        rows = edited_df.to_dict("records")
        added, skipped, invalid_team = [], [], []
        for row in rows:
            name = str(row.get("고객사명", "")).strip()
            team = str(row.get("담당부서", "")).strip()
            if not name:
                continue
            if team not in TEAMS:
                invalid_team.append(name)
                continue
            ok = add_client(
                client_ws,
                name=name,
                kakao_id=_extract_id_from_url("kakao", str(row.get("카카오ID_또는_URL", ""))),
                naver_id=_extract_id_from_url("naver", str(row.get("네이버ID_또는_URL", ""))),
                active=True,
                team=team,
            )
            (added if ok else skipped).append(name)

        st.cache_data.clear()
        if added:
            st.toast(f"{len(added)}건 등록 완료: {', '.join(added)}", icon="✅")
        if skipped:
            st.toast(f"이미 존재해서 건너뜀: {', '.join(skipped)}", icon="⚠️")
        if invalid_team:
            st.toast(f"담당부서 값이 잘못돼서 건너뜀: {', '.join(invalid_team)}", icon="⚠️")
        if added:
            st.rerun()

    st.divider()
    st.write("**방법 2. 엑셀/CSV 파일 업로드**")
    st.caption("컬럼명이 정확히 '고객사명', '담당부서', '카카오ID_또는_URL', '네이버ID_또는_URL'이어야 합니다.")
    uploaded_file = st.file_uploader("파일 선택", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                upload_df = pd.read_csv(uploaded_file)
            else:
                upload_df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"파일을 읽는 중 오류: {e}")
            upload_df = None

        if upload_df is not None:
            st.write("미리보기:")
            st.dataframe(upload_df, use_container_width=True)

            if st.button("📥 이 파일 내용으로 일괄 등록", type="primary"):
                added, skipped, invalid_team = [], [], []
                for _, row in upload_df.iterrows():
                    name = str(row.get("고객사명", "")).strip()
                    team = str(row.get("담당부서", "")).strip()
                    if not name or name == "nan":
                        continue
                    if team not in TEAMS:
                        invalid_team.append(name)
                        continue
                    ok = add_client(
                        client_ws,
                        name=name,
                        kakao_id=_extract_id_from_url("kakao", str(row.get("카카오ID_또는_URL", ""))),
                        naver_id=_extract_id_from_url("naver", str(row.get("네이버ID_또는_URL", ""))),
                        active=True,
                        team=team,
                    )
                    (added if ok else skipped).append(name)

                st.cache_data.clear()
                if added:
                    st.toast(f"{len(added)}건 등록 완료: {', '.join(added)}", icon="✅")
                if skipped:
                    st.toast(f"이미 존재해서 건너뜀: {', '.join(skipped)}", icon="⚠️")
                if invalid_team:
                    st.toast(f"담당부서 값이 잘못돼서 건너뜀: {', '.join(invalid_team)}", icon="⚠️")
                if added:
                    st.rerun()
