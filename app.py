"""
앱 진입점(라우터). Streamlit Cloud의 'Main file path'는 배포 후 변경이
안 되기 때문에, 파일명(app.py)은 그대로 두고 여기서 st.navigation으로
사이드바에 표시될 이름을 자유롭게 지정한다.

실제 Main 대시보드 내용은 app_main.py에 있음.
"""
import streamlit as st

st.set_page_config(page_title="리뷰 모니터링", page_icon="📊", layout="wide")

main_page = st.Page("app_main.py", title="Main", icon="📊", default=True)
client_page = st.Page("pages/1_고객사.py", title="고객사", icon="🩺")
monitor_page = st.Page("pages/2_모니터링현황.py", title="모니터링현황", icon="📡")
alert_page = st.Page("pages/3_리뷰감지.py", title="리뷰감지", icon="⚠️")
kakao_page = st.Page("pages/4_카카오리뷰확인.py", title="카카오리뷰확인", icon="💬")

pg = st.navigation([main_page, client_page, monitor_page, alert_page, kakao_page])
pg.run()
