import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# --- [설정] 매핑 정보 및 키워드 ---
SAMSUNG_MAPPING = {
    "헬시체크(일반-스트레스/면역) [외부]": "ms50_Healthycheck12",
    "조기 헬시체크(스트레스/면역) [외부]": "ms50_Healthycheck12",
    "암특화 온코체크 (남성 암 12종) [외부]": "ms48_Oncocare12/13_M",
    "암특화 온코체크 (여성 암 13종) [외부]": "ms49_Oncocare12/13_F",
    "토탈체크 (남성 암/일반 질환 48종) [외부]": "ms46_Totalcheck48/51_M",
    "토탈체크 (여성 암/일반 질환 51종) [외부]": "ms47_Totalcheck48/51_F",
    "뷰티체크 12종 여(피부8종/모발4종)": "BeautyCheck12_F",
    "뷰티체크 12종 남(피부8종/모발4종)": "BeautyCheck12_M"
}

COLUMN_KEYWORDS = {
    'samsung_seq_num': ['순번', 'no'],
    'samsung_specimen_num': ['검체번호', '검체'],
    'samsung_collection_date': ['채혈일'],
    'birth_date': ['생년2자리', '생년월일', '생일', '출생'],
    'gender': ['s/a', '성별', 'gender', 'sex', '성'],
    'inspection_item': ['검사항목', '검사', '항목'],
    'name': ['성명', '이름', 'name', '환자명'],
}

# --- [유틸리티] 데이터 정제 함수 ---
def _find_column(df, keyword_type):
    keywords = COLUMN_KEYWORDS.get(keyword_type, [])
    for col in df.columns:
        if any(keyword.lower() == str(col).lower() for keyword in keywords):
            return col
    return None

def clean_date_final(val):
    if pd.isna(val) or str(val).lower() == 'nan': return ""
    s = str(val).strip()
    s = re.sub(r'[^\d\.\-]', '', s).replace('.', '-')
    if len(s) >= 10:
        match = re.search(r'(\d{4}-\d{2}-\d{2})', s)
        if match: return match.group(1)
    return s

def format_birth_year(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    if '-' in s and len(s) >= 4: return s[:4]
    if len(s) >= 8 and s.isdigit(): return s[:4]
    return s[:4] if len(s) >= 4 else s

# --- [삼성창원] 변환 로직 (V4 로직 이식) ---
def process_samsung_logic(df):
    seq_col = _find_column(df, 'samsung_seq_num')
    spec_col = _find_column(df, 'samsung_specimen_num')
    gen_col = _find_column(df, 'gender')
    birth_col = _find_column(df, 'birth_date')
    date_col = _find_column(df, 'samsung_collection_date')
    item_col = _find_column(df, 'inspection_item')
    
    paper_col = next((c for c in df.columns if '종이결과지' in str(c)), None)
    eng_col = next((c for c in df.columns if '영문결과지' in str(c)), None)
    for_col = next((c for c in df.columns if '외국인' in str(c)), None)

    if not all([seq_col, spec_col, gen_col, birth_col, date_col, item_col]):
        return None, None

    res = pd.DataFrame()
    res['순번'] = df[seq_col]
    res['영문결과지'] = df[eng_col].apply(lambda x: '영문' if str(x).strip().upper() == 'Y' else '') if eng_col else ''
    res['외국인'] = df[for_col].apply(lambda x: 'Other' if str(x).strip().upper() == 'Y' else 'Korean') if for_col else 'Korean'
    res['1차의뢰기관'] = '삼성창원병원'; res['2차의뢰기관'] = '삼성창원병원'
    res[''] = ''; res[' '] = ''; res['  '] = ''
    res['검체번호'] = df[spec_col]
    res['샘플상태'] = 'Blood'
    res['생년월일'] = df[birth_col].apply(format_birth_year)
    res['성별'] = df[gen_col]
    res['채혈일'] = df[date_col].apply(clean_date_final)
    res['동의일'] = res['채혈일']
    res['검사항목'] = df[item_col].apply(lambda x: SAMSUNG_MAPPING.get(str(x).strip(), str(x)))
    res['_원본항목'] = df[item_col]
    res['결과발송'] = df[paper_col].apply(lambda x: 'PDF/인쇄' if str(x).strip().upper() == 'Y' else 'PDF/API') if paper_col else 'PDF/API'

    # 중복 검체 처리 (뷰티체크 우선 분리)
    res['_to_sep'] = False
    beauty_items = ['뷰티체크 12종 여(피부8종/모발4종)', '뷰티체크 12종 남(피부8종/모발4종)']
    
    for sn, group in res.groupby('검체번호', sort=False):
        if len(group) > 1:
            indices = group.index.tolist()
            beauty_idxs = [i for i in indices if res.at[i, '_원본항목'] in beauty_items]
            other_idxs = [i for i in indices if i not in beauty_idxs]
            sep_idxs = beauty_idxs + other_idxs[1:] if beauty_idxs else indices[1:]
            for idx in sep_idxs: res.at[idx, '_to_sep'] = True

    normal = res[~res['_to_sep']].copy()
    separate = res[res['_to_sep']].copy()
    
    final_df = pd.concat([normal, pd.DataFrame([['']*len(res.columns)], columns=res.columns), separate], ignore_index=True) if not separate.empty else normal
    return final_df.drop(columns=['_원본항목', '_to_sep']), None

# --- [유젠스] 로직 (V4 로직 및 버그 수정 반영) ---
def process_ugens_logic(df, blood_df):
    if df.iloc[0, 0] == '번호':
        df.columns = df.iloc[0]; df = df[1:].reset_index(drop=True)
    
    valid_barcodes = set()
    if blood_df is not None:
        for col in blood_df.columns:
            for val in blood_df[col].dropna():
                b_str = str(val).strip()
                if len(b_str) >= 7: valid_barcodes.add(b_str)
        
        bc_col = next((c for c in df.columns if '바코드' in str(c) or 'Kit ID' in str(c)), None)
        if bc_col:
            df = df[df[bc_col].astype(str).str.strip().isin(valid_barcodes)].copy()

    res_list = []
    target_kws = ['부평세림', '뉴고려', '진헬스','사랑의']

    for idx, row in df.iterrows():
        h_name = str(row['병원명']).strip()
        if '진헬스' in h_name: h_name = '진헬스의원'
        
        raw_codes = str(row['서비스코드']).strip()
        codes = [c.strip() for c in raw_codes.split(',')] if ',' in raw_codes else [raw_codes]
        
        for c in codes:
            new_row = {
                '병원명': h_name, '': '', ' ': '', '  ': '',
                '검체 바코드 번호(Kit ID)': str(row.get('검체 바코드 번호(Kit ID)', row.get('Kit ID', ''))).strip(),
                '샘플상태': 'Blood',
                '출생연도': str(row.get('출생연도', ''))[:4],
                '성별': 'M' if str(row.get('성별', '')).strip() in ['남', 'M'] else 'F',
                '검체채취일': clean_date_final(row.get('검체채취일')),
                '동의서 및 의뢰서': clean_date_final(row.get('동의서 및 의뢰서')),
                '서비스코드': c
            }
            if any(kw in h_name for kw in target_kws) and c.lower() == 'ugenslife20':
                new_row['서비스코드'] = 'ms44_Ugenslife20'
            res_list.append(new_row)
            
    return pd.DataFrame(res_list), None

# --- [UI] 메인 화면 ---
st.title("🏥 엑셀 서식 변환기")
mode = st.radio("작업 대상을 선택하세요", ["삼성창원병원", "유젠스(U-GENS)"], horizontal=True)

if mode == "삼성창원병원":
    st.subheader("📍 삼성창원병원 변환 모드")
    f_samsung = st.file_uploader("삼성 원본 파일을 업로드하세요", type=['xlsx'], key="s_up")
    if f_samsung:
        if st.button("🚀 삼성창원 변환 시작"):
            df_s = pd.read_excel(f_samsung, dtype=str)
            res_s, err = process_samsung_logic(df_s)
            if res_s is not None:
                st.success("✅ 삼성창원 변환 완료!")
                st.dataframe(res_s)
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    res_s.to_excel(writer, index=False)
                st.download_button("📥 삼성창원 결과 다운로드", out.getvalue(), f"삼성창원_변환_{datetime.now().strftime('%m%d')}.xlsx")

elif mode == "유젠스(U-GENS)":
    st.subheader("📍 유젠스 통합 변환 모드")
    col1, col2 = st.columns(2)
    with col1: f_main = st.file_uploader("1. RawData 업로드", type=['xlsx'], key="u_raw")
    with col2: f_bc = st.file_uploader("2. 바코드 파일 업로드", type=['xlsx'], key="u_bc")
    
    if f_main and f_bc:
        if st.button("🚀 유젠스 통합 변환 시작"):
            df_m = pd.read_excel(f_main, dtype=str)
            df_b = pd.read_excel(f_bc, header=None, dtype=str)
            final_df, err = process_ugens_logic(df_m, df_b)
            if final_df is not None:
                st.success(f"✅ 유젠스 변환 완료! (총 {len(final_df)}건)")
                st.dataframe(final_df)
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    final_df.to_excel(writer, index=False)
                st.download_button("📥 유젠스 통합 결과 다운로드", out.getvalue(), f"유젠스_통합_{datetime.now().strftime('%m%d')}.xlsx")