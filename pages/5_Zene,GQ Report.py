import streamlit as st
import pandas as pd
import io
import os

st.set_page_config(page_title="QC Report Generator", layout="wide")

# --- [로직] 데이터 병합 및 준비 ---
def prepare_data(df_orig, df_qc, order_number):
    filtered_df = df_orig[df_orig['ORDER #'] == order_number].copy()
    if filtered_df.empty: return None

    merged_df = filtered_df
    if df_qc is not None and not df_qc.empty:
        qc_cols = ['SPL.', 'Conc.(ng/ul)']
        if 'QC RESULT' in df_qc.columns: qc_cols.append('QC RESULT')
        
        merged_df = pd.merge(filtered_df, df_qc[qc_cols], on='SPL.', how='left', suffixes=('', '_qc'))
        replaced_rows = merged_df['Conc.(ng/ul)_qc'].notna()
        
        # 데이터 업데이트
        merged_df['Conc.(ng/ul)'] = merged_df['Conc.(ng/ul)_qc'].fillna(merged_df['Conc.(ng/ul)'])
        if 'QC RESULT_qc' in merged_df.columns:
            merged_df.loc[replaced_rows, 'QC RESULT'] = merged_df.loc[replaced_rows, 'QC RESULT_qc']
            
        # 업데이트된 행을 맨 위로 올리기
        merged_df = pd.concat([merged_df[replaced_rows], merged_df[~replaced_rows]])
        merged_df.drop(columns=[col for col in merged_df.columns if col.endswith('_qc')], inplace=True)
        
    return merged_df

# --- [로직] QC Report 생성 ---
def create_report_data(merged_df, order_number):
    df = merged_df.copy()
    df['Volume(ul)'] = 20
    df['Conc.(ng/ul)'] = pd.to_numeric(df['Conc.(ng/ul)'], errors='coerce').fillna(0)
    df['Total Amount(ng)'] = df['Conc.(ng/ul)'] * df['Volume(ul)']
    
    df['REASON FOR FAIL'] = df.apply(
        lambda r: 'Concentration' if r['Conc.(ng/ul)'] < 10 and str(r.get('QC RESULT', '')) == 'Fail' else '', axis=1
    )
    
    report_df = df[['ORDER #', 'SPL.', 'Conc.(ng/ul)', 'Volume(ul)', 'Total Amount(ng)', 'QC RESULT', 'REASON FOR FAIL']]
    inst = df['의뢰기관'].iloc[0].replace(' inc', '') if '의뢰기관' in df.columns else "Unknown"
    
    # 통계 요약
    total = len(report_df)
    pass_c = len(report_df[report_df['QC RESULT'] == 'Pass'])
    fail_c = len(report_df[report_df['QC RESULT'] == 'Fail'])
    fail_rate = (fail_c / total * 100) if total > 0 else 0
    max_c = df['Conc.(ng/ul)'].max() if total > 0 else 0
    min_c = df['Conc.(ng/ul)'].min() if total > 0 else 0

    summary_txt = (
        f"[{order_number} {inst} QC 결과 요약]\n"
        f"----------------------------------------\n"
        f"Total samples : {total}\n"
        f"Pass samples : {pass_c}\n"
        f"Fail samples : {fail_c}\n\n"
        f"Fail Rate : {fail_rate:.1f} %\n"
        f"Max Conc. : {max_c:.2f} ng/ul\n"
        f"Min Conc. : {min_c:.2f} ng/ul\n"
        f"----------------------------------------"
    )
    filename = f"{order_number}_{inst}_QC_{total}_{pass_c}_{fail_c}_Sample Check List.xlsx"
    return report_df, summary_txt, filename

# --- [로직] 추가 파일 (final_output_with_blanks) 생성 ---
def create_additional_data(merged_df):
    df = merged_df.copy()
    is_genequest = '의뢰기관' in df.columns and 'Genequest inc' in df['의뢰기관'].values
    
    if is_genequest:
        # [Genequest] 로직
        cols = ['ORDER #', 'WKST. ID', 'Plate Pos.', 'MG ID', 'SPL.', 'SPL. STATUS', 'Conc.(ng/ul)', 'QC RESULT']
        for c in cols: 
            if c not in df.columns: df[c] = ''
        
        reordered = df[cols].copy()
        reordered['Prep date'] = reordered['WKST. ID'].apply(
            lambda x: f"20{str(x)[3:5]}-{str(x)[5:7]}-{str(x)[7:9]}" if isinstance(x, str) and len(x) >= 9 else ''
        )
        reordered['QC date'] = reordered['Prep date']
        
        # 빈 컬럼 및 No. 삽입
        reordered.insert(1, 'Empty 1', '')
        reordered.insert(2, 'Empty 2', '')
        reordered.insert(5, 'Empty 3', '')
        reordered.insert(0, 'No.', range(1, len(reordered) + 1))
        reordered['Empty 4'] = ''
        reordered['Empty 5'] = ''
        reordered['Empty 6'] = ''
        reordered['QC RESULT'] = df['QC RESULT']
        
        final_cols = [
            'No.', 'ORDER #', 'Empty 1', 'Empty 2', 'WKST. ID', 'Plate Pos.', 'Empty 3', 'MG ID', 
            'SPL.', 'SPL. STATUS', 'Conc.(ng/ul)', 'Empty 4', 'Empty 5', 'Prep date', 'QC date', 
            'Empty 6', 'QC RESULT'
        ]
        return reordered[final_cols], True
    else:
        # [Zene / 기타] 로직
        try:
            # 1, 13, 14, 16, 17, 19번째 열 삭제
            cols_to_keep = [col for i, col in enumerate(df.columns) if i not in [1, 13, 14, 16, 17, 19]]
            reordered = df[cols_to_keep].copy()
            if not reordered.empty:
                reordered.columns.values[0] = 'No'
            reordered['No'] = range(1, len(reordered) + 1)
            
            # 날짜 앞에 작은따옴표(') 붙여서 텍스트화
            for col in ['등록일자', '납기일']:
                if col in reordered.columns:
                    dates = pd.to_datetime(reordered[col], errors='coerce')
                    formatted = dates.dt.strftime('%Y-%m-%d')
                    final_str = formatted.mask(dates.isna(), '')
                    reordered[col] = final_str.apply(lambda x: f"'{x}" if x else x).astype(str)
            return reordered, False
        except Exception as e:
            st.error(f"추가 파일 폼 생성 중 오류: {e}")
            return None, False

# --- [엑셀 저장 로직 (텍스트 포맷 강제)] ---
def get_excel_bytes(df, is_genequest):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        if not is_genequest:
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            text_format = workbook.add_format({'num_format': '@'})
            for col_name in ['등록일자', '납기일']:
                if col_name in df.columns:
                    idx = df.columns.get_loc(col_name)
                    worksheet.set_column(idx, idx, None, text_format)
    return output.getvalue()


# --- [UI] ---
st.title("📊 QC Report Generator")
st.info("💡 Zene, Genequest 데이터의 QC 진행현황을 병합하고 맞춤형 레포트를 생성합니다.")

col1, col2 = st.columns(2)
with col1:
    f_orig = st.file_uploader("1. 원본 데이터 업로드 (필수)", type=['xlsx'])
with col2:
    f_qc = st.file_uploader("2. QC 진행현황 업로드 (선택)", type=['xlsx'])

if f_orig:
    try:
        df_orig = pd.read_excel(f_orig)
        req_cols = ['ORDER #', '의뢰기관']
        if not all(c in df_orig.columns for c in req_cols):
            st.error(f"❌ 원본 데이터에 필수 컬럼 {req_cols}이 누락되었습니다.")
        else:
            df_qc = pd.read_excel(f_qc) if f_qc else None
            
            # 대상 기관 필터링 (없으면 전체)
            targets = ['Genequest inc', 'Zene inc']
            filtered_df = df_orig[df_orig['의뢰기관'].isin(targets)]
            if filtered_df.empty:
                st.warning("⚠️ Genequest나 Zene에 해당하는 수주가 없어 전체 목록을 표시합니다.")
                filtered_df = df_orig
            
            # 수주 번호 드롭다운 리스트 생성
            unique_orders = filtered_df[['ORDER #', '의뢰기관']].drop_duplicates().sort_values(by='ORDER #')
            display_dict = {f"[{row['의뢰기관'].replace(' inc', '')}] {row['ORDER #']}": row['ORDER #'] for _, row in unique_orders.iterrows()}
            
            selected_display = st.selectbox("3. 수주 번호를 선택하세요:", list(display_dict.keys()))
            selected_order = display_dict[selected_display]
            
            if st.button("🚀 4. QC 레포트 생성", type="primary"):
                with st.spinner("데이터 병합 및 분석 중..."):
                    # 1. 데이터 병합
                    merged_df = prepare_data(df_orig, df_qc, selected_order)
                    
                    if merged_df is not None:
                        # 2. 리포트 및 요약 생성
                        report_df, summary_txt, report_name = create_report_data(merged_df, selected_order)
                        
                        # 3. 추가 빈칸 폼 파일 생성
                        add_df, is_gq = create_additional_data(merged_df)
                        add_bytes = get_excel_bytes(add_df, is_gq) if add_df is not None else None
                        
                        st.success("✅ 레포트 생성 완료!")
                        
                        # 결과 요약본 표시 (사용자가 쉽게 복사 가능)
                        st.code(summary_txt, language='text')
                        
                        c3, c4 = st.columns(2)
                        with c3:
                            out_report = io.BytesIO()
                            report_df.to_excel(out_report, index=False, engine='xlsxwriter')
                            st.download_button(
                                "📥 QC Report (Sample Check List) 다운로드",
                                data=out_report.getvalue(),
                                file_name=report_name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        with c4:
                            if add_bytes:
                                st.download_button(
                                    "📥 추가 폼 (final_output_with_blanks) 다운로드",
                                    data=add_bytes,
                                    file_name="final_output_with_blanks.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
    except Exception as e:
        st.error(f"파일 처리 중 오류가 발생했습니다: {e}")