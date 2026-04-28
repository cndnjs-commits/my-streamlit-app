import streamlit as st

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Macrogen 업무 자동화 시스템",
    page_icon="🧬",
    layout="wide"
)

# --- 타이틀 및 안내 ---
st.title("🧬 사내 업무 자동화 시스템")
st.markdown("---")
st.info("💡 **사용 방법**: 왼쪽 사이드바 메뉴에서 실행할 도구를 선택해 주세요.")

# --- 1열 (1번, 2번 도구) ---
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("🏥 1. 엑셀 서식 변환기")
        st.write("""
        **[유젠스, 삼성창원]**
        - 병원별 맞춤형 서식 자동 변환 및 순번 부여
        - 삼성창원 중복 샘플 자동 분리 및 색상 서식 적용
        - 유젠스 바코드 필터링 및 `ms44` 서비스 코드 치환
        """)

with col2:
    with st.container(border=True):
        st.subheader("📄 2. 우리원 OCR 추출기")
        st.write("""
        **[우리원 전용]**
        - PDF 의뢰서 성명, 차트번호, 검사항목 자동 추출
        - '한글 소거법' 알고리즘으로 이름/차트 뭉침 해결
        - 한 사람의 여러 검사 항목 자동 행 분리 및 순번 부여
        """)

st.write("") 

# --- 2열 (3번, 4번 도구) ---
col3, col4 = st.columns(2)

with col3:
    with st.container(border=True):
        st.subheader("🧪 3. 플레이트 시각화 도구")
        st.write("""
        **[샘플 위치 확인]**
        - 96-Well Plate 위치 히트맵 실시간 시각화
        - A1-H12 셀별 고유 번호(1-96번) 매핑
        - 검색된 SPL ID 셀 내 줄바꿈 자동 표시
        """)

with col4:
    with st.container(border=True):
        st.subheader("🧬 4. 인체유래물 데이터 분류기")
        st.write("""
        **[DTC 샘플 처리]**
        - DTC, 인체유래물 동의, Analysis 완료 샘플 필터링 (RE 제외)
        - 농도(Tot AM) 기준 2.5 이상 / 1.25 이상 시트 자동 분할
        - WKST ID(날짜 추출) 및 Plate 위치 기반 다중 정렬
        """)

st.write("")

# --- 3열 (5번, 6번 도구) ---
col5, col6 = st.columns(2)

with col5:
    with st.container(border=True):
        st.subheader("📊 5. QC 레포트 생성기")
        st.write("""
        **[Zene / Genequest]**
        - 원본 데이터와 QC 진행현황 자동 병합
        - 통계 요약본 생성 및 맞춤형 Blank 폼 생성
        - 엑셀 날짜 형식 텍스트 강제 변환 오류 방지
        """)

with col6:
    with st.container(border=True):
        st.subheader("📂 6. Storage Position 변경기")
        st.write("""
        **[Chip Plate Data]**
        - Chip Plate Export 파일(CSV) 업로드 지원
        - 파일명 기반 ChipPlateID 자동 추출 
        - StoreTubeID 자동 조합 및 신규 양식 생성
        """)

st.write("")

# --- 하단 시스템 안내 ---
with st.expander("📌 시스템 이용 안내"):
    st.write("""
    - **독립 작동**: 각 메뉴의 기능은 서로 간섭 없이 독립적으로 작동합니다.
    - **오류 해결**: 처리 중 알 수 없는 오류가 발생하거나 화면이 멈춘 경우, 키보드의 `F5`를 눌러 페이지를 새로고침 해주세요.
    - **보안**: 모든 데이터 변환과 추출은 이 PC/서버 내부에서만 이루어지며 외부로 유출되지 않습니다.
    """)

st.divider()
st.caption("© 2026 Macrogen. 내부 업무 효율화를 위해 개발된 전용 도구입니다.")
