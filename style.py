"""
전체 앱 공통 스타일. 각 페이지 맨 위에서 inject_css()를 호출해서 사용.
"""
import streamlit as st

PULSE_SVG = """
<svg width="120" height="24" viewBox="0 0 120 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <polyline points="0,12 25,12 32,4 40,20 48,2 56,22 64,12 120,12"
    stroke="#E8A23D" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'IBM Plex Sans', sans-serif;
    }}

    h1, h2, h3 {{
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 600;
        color: #1A2B4C;
        letter-spacing: -0.01em;
    }}

    /* 사이드바 */
    [data-testid="stSidebar"] {{
        background-color: #1A2B4C;
    }}
    [data-testid="stSidebar"] * {{
        color: #F1F3F6 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: #F1F3F6 !important;
    }}

    /* 메트릭 카드 */
    [data-testid="stMetric"] {{
        background-color: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-left: 4px solid #1A2B4C;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        color: #1A2B4C;
    }}
    [data-testid="stMetricLabel"] {{
        color: #667085;
        font-size: 0.85rem;
    }}

    /* 버튼 */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid #D0D5DD;
    }}
    .stButton > button[kind="primary"] {{
        background-color: #1A2B4C;
        border: none;
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #2A3F6C;
    }}

    /* 카드형 컨테이너 (border=True 컨테이너) */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 10px !important;
    }}

    /* 데이터프레임 헤더 */
    [data-testid="stDataFrame"] {{
        border-radius: 8px;
        overflow: hidden;
    }}

    /* expander */
    [data-testid="stExpander"] {{
        border-radius: 8px;
        border: 1px solid #E4E7EC;
    }}

    /* 숫자 강조용 유틸 클래스 (직접 쓸 때) */
    .mono-number {{
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
    }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """펄스 라인 + 제목 + (선택)부제목을 그리는 공통 헤더."""
    pulse_inline = PULSE_SVG.replace("\n", "").strip()
    html = (
        f'<div style="display:flex; align-items:center; gap:14px; margin-bottom:4px;">'
        f'{pulse_inline}'
        f'<div style="font-family:\'IBM Plex Sans\', sans-serif; font-weight:700; font-size:1.6rem; color:#1A2B4C;">{title}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)
    st.write("")
