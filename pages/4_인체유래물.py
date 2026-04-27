import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

st.set_page_config(page_title="인체유래물 데이터 분류", layout="wide")

# --- [로직] 정렬 키 생성 함수 ---
def custom_sort_key(plate_pos):
    """플레이트/저장 위치 정렬 키 (예: A1 -> ('A', 1))"""
    match = re.match(r"([a-zA-Z]+)(\d+)", str(plate_pos))
    if match:
        letter, number = match.groups()
        return (letter.upper(), int(number))
    return (str(plate_pos), 0)

def wkst_id_sort_key(wkst_id):
    """WKST. ID 정렬 키 (날짜와 영문/숫자 분리)"""
    wkst_str = str(wkst_id).strip()
    
    # HPW/HSP + YYMMDD + 영문 + 숫자 형태
    match = re.match(r"(?:HPW|HSP)(\d{2})(\d{2})(\d{2})([a-zA-Z]*)(\d+)", wkst_str, re.IGNORECASE)
    if match:
        yy, mm, dd, letter, seq = match.groups()
        return (int(yy), int(mm), int(dd), letter.upper() if letter else '', int(seq))
    
    # 일반적인 영문+숫자+영문+숫자 패턴
    match = re.match(r"([a-zA-Z]+)(\d+)([a-zA-Z]+)(\d+)", wkst_str)
    if match:
        prefix1, number1, prefix2, number2 = match.groups()
        return (99, 99, 99, (prefix1 + prefix2).upper(), int(number1) * 10000 + int(number2))
    
    # 영문+숫자 패턴
    match = re.match(r"([a-zA-Z]+)(\d+)", wkst_str)
    if match:
        prefix, number = match.groups()
        return (99, 99, 99, prefix.upper(), int(number))
    
    return (99, 99, 99, wkst_str.upper(), 0)

def get_month_name(month_num):
    """월 번호를 한국어 월 이름으로 변환"""
    return f"{month_num}월"

def extract_month_from_wkst(wkst_id):
    """WKST. ID에서 월 정보 추출 (5~6번째 자리)"""
    if pd.isna(wkst_id): return None
    wkst_str = str(wkst_id).strip()
    
    if wkst_str.upper().startswith(('HPW', 'HSP')) and len(wkst_str) >= 7:
        month_part = wkst_str[5:7]
        if month_part.isdigit():
            month_num = int(month_part)
            if 1 <= month_num <= 12:
                return month_num
    return None

def sort_dataframe(df):
    """데이터프레임 다중 조건 정렬 및 NO 컬럼 추가"""
    if df.empty: return df
    
    df_work = df.drop('월', axis=1, errors='ignore').copy()
    
    # 정렬용 임시 튜플 컬럼 생성
    df_work['wkst_sort'] = df_work['WKST. ID'].apply(wkst_id_sort_key)
    df_work['storage_sort'] = df_work['STORAGE POSITION'].apply(custom_sort_key)
    df_work['plate_sort'] = df_work['Plate Pos.'].apply(custom_sort_key)
    
    # WKST ID -> Storage Pos -> Plate Pos 순서로 정렬
    df_sorted = df_work.sort_values(by=['wkst_sort', 'storage_sort', 'plate_sort'])
    df_sorted = df_sorted.drop(['wkst_sort', 'storage_sort', 'plate_sort'], axis=1)
    
    # NO 컬럼 추가
    df_sorted.insert(0, 'NO', range(1, len(df_sorted) + 1))
    return df_sorted

# --- [UI] 메인 화면 ---
st.title("📊 인체유래물 데이터 분류 및 정렬")
st.info("💡 **DTC 샘플**을 필터링하여 농도(`Tot AM`) 기준 **월별/구간별 시트**로 분할 생성합니다.")

uploaded_file = st.file_uploader("원본 Excel 데이터를 업로드하세요", type=['xlsx', 'xls'])

if uploaded_file:
    if st.button("🚀 데이터 분류 및 정렬 시작", type="primary"):
        try:
            with st.spinner("데이터 분석 및 분할 중..."):
                df = pd.read_excel(uploaded_file, sheet_name='Sheet')
                
                # 1. 필수 컬럼 검증
                required_cols = [
                    'ORDER #', '거래처 구분 코드', 'MG ID', 'SPL.', 'WKST. ID', 'Plate Pos.', 
                    'STORAGE POSITION', '인체유래물 기증 동의', 'Conc.(ng/ul)', 'Chip #', 
                    'Chip Position', '검체 채취일', 'PLATFORM', 'Work Status'
                ]
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    st.error(f"❌ 필수 컬럼이 누락되었습니다: {', '.join(missing_cols)}")
                    st.stop()

                # 2. 데이터 필터링
                original_len = len(df)
                filtered_df = df[
                    (df['거래처 구분 코드'] == 'DTC') & 
                    (df['인체유래물 기증 동의'] == 'Y') &
                    (df['Work Status'] == 'Analysis 완료') &
                    ~df['SPL.'].astype(str).str.contains('RE', case=False, na=False)
                ].copy()
                
                if filtered_df.empty:
                    st.warning("⚠️ 필터링 조건을 만족하는 데이터가 없습니다.")
                    st.stop()
                    
                # 3. 데이터 변환 및 컬럼 추가
                filtered_df = filtered_df[required_cols].copy()
                filtered_df['Tot AM(ug)'] = (pd.to_numeric(filtered_df['Conc.(ng/ul)'], errors='coerce').fillna(0) * 40) / 1000
                filtered_df['260/280'] = ''
                filtered_df['월'] = filtered_df['WKST. ID'].apply(extract_month_from_wkst)
                
                extracted_months = sorted(filtered_df['월'].dropna().unique())
                
                if not extracted_months:
                    st.error("❌ 처리할 월 정보를 추출할 수 없습니다. (WKST. ID 형식을 확인하세요)")
                    st.stop()

                # 4. 월별 / 농도별 데이터 분할
                monthly_data = {}
                log_messages = []
                
                for month_num in extracted_months:
                    month_name = get_month_name(int(month_num))
                    month_df = filtered_df[filtered_df['월'] == month_num].copy()
                    
                    # 2.5 이상
                    high_df = month_df[month_df['Tot AM(ug)'] >= 2.5].copy()
                    if not high_df.empty:
                        monthly_data[f'{month_name} 2.5이상'] = high_df
                    
                    # 1.25 이상 ~ 2.5 미만
                    mid_df = month_df[(month_df['Tot AM(ug)'] >= 1.25) & (month_df['Tot AM(ug)'] < 2.5)].copy()
                    if not mid_df.empty:
                        monthly_data[f'{month_name} 1.25이상 2.5미만'] = mid_df
                        
                    log_messages.append(f"- **{month_name}**: 2.5이상 (`{len(high_df)}`개) / 1.25이상~2.5미만 (`{len(mid_df)}`개)")

                if not monthly_data:
                    st.warning("⚠️ 농도 조건(1.25 이상)을 만족하는 데이터가 없습니다.")
                    st.stop()

                # 5. 데이터 정렬 및 엑셀 생성
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='openpyxl') as writer:
                    for sheet_name, df_to_sort in monthly_data.items():
                        sorted_df = sort_dataframe(df_to_sort)
                        safe_sheet_name = sheet_name[:31] # 엑셀 시트명 제한 방어
                        sorted_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                
                # --- 결과 요약 출력 ---
                st.success("✅ 데이터 분류 및 정렬이 완료되었습니다!")
                
                with st.expander("📊 처리 결과 요약 보기", expanded=True):
                    st.write(f"**전체 데이터**: {original_len:,}개 → **필터링 후**: {len(filtered_df):,}개")
                    for msg in log_messages:
                        st.write(msg)
                
                # 6. 다운로드 버튼
                st.download_button(
                    label="📥 분류 및 정렬된 Excel 다운로드",
                    data=out.getvalue(),
                    file_name=f"인체유래물_분류결과_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"❌ 데이터 처리 중 오류가 발생했습니다: {e}")