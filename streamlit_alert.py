"""
기존 Streamlit 앱 메인 파일 상단에서 아래처럼 호출하면 됩니다.

    from streamlit_alert import show_negative_review_alert
    show_negative_review_alert()

status='신규' & is_negative='TRUE' 인 리뷰가 있으면 모달 경고창을 띄우고,
'확인했습니다' 버튼을 누르면 해당 행들의 status를 '확인됨'으로 일괄 업데이트합니다.
"""
import streamlit as st
from sheets_schema import open_spreadsheet, REVIEW_SHEET


@st.cache_data(ttl=60)  # 1분 캐시: 대시보드 새로고침마다 매번 시트를 읽지 않도록
def _load_review_rows():
    sh = open_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    records = ws.get_all_records()
    return records


def _mark_as_checked(review_ids: set):
    sh = open_spreadsheet()
    ws = sh.worksheet(REVIEW_SHEET)
    all_values = ws.get_all_values()
    header = all_values[0]
    id_col = header.index("리뷰ID")
    status_col = header.index("status")

    updates = []
    for row_idx, row in enumerate(all_values[1:], start=2):  # 2행부터 (1행은 헤더)
        if row[id_col] in review_ids:
            updates.append({
                "range": f"{chr(65 + status_col)}{row_idx}",
                "values": [["확인됨"]],
            })
    if updates:
        ws.batch_update(updates)

    st.cache_data.clear()


@st.dialog("⚠️ 신규 부정 리뷰 발생")
def _alert_dialog(negative_rows):
    st.write(f"확인되지 않은 부정 리뷰가 **{len(negative_rows)}건** 있습니다.")

    by_client = {}
    for row in negative_rows:
        by_client.setdefault(row["고객사명"], []).append(row)

    for client_name, rows in by_client.items():
        with st.expander(f"{client_name} ({len(rows)}건)", expanded=True):
            for row in rows:
                st.markdown(
                    f"**[{row['플랫폼']}]** ⭐{row.get('별점', '-')}  \n"
                    f"{row.get('리뷰내용', '')}  \n"
                    f"_판단근거: {row.get('판단근거', '')}_"
                )
                st.divider()

    if st.button("모두 확인했습니다", type="primary"):
        ids = {row["리뷰ID"] for row in negative_rows}
        _mark_as_checked(ids)
        st.rerun()


def show_negative_review_alert():
    """메인 앱에서 호출. 신규 부정 리뷰가 있을 때만 모달을 띄움."""
    rows = _load_review_rows()
    negative_rows = [
        r for r in rows
        if str(r.get("status", "")).strip() == "신규"
        and str(r.get("is_negative", "")).strip().upper() == "TRUE"
    ]

    if negative_rows:
        _alert_dialog(negative_rows)
