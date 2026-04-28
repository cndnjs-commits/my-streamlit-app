import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Storage Position 변경기", layout="wide")

st.title("📂 Storage Position 변경기")
st.info("💡 **Chip 실험 Work**에서 다운로드한 **Chip Plate Export 파일(CSV)**을 업로드하여 Storage Position(`StoreTubeID`)을 자동 생성합니다.")

# 사용법 안내
with st.expander("📖 사용 방법", expanded=True):
    st.write("""
    1. Chip 실험 Work에서 **Chip Plate Export 파일(.csv)**을 다운로드합니다.
    2. 아래 업로드 칸에 해당 파일을 업로드합니다.
    3. 아래 미리보기 표에서 데이터가 제대로 매핑되었는지 확인합니다.
    4. **CSV 다운로드** 버튼을 눌러 결과물을 저장합니다.
    """)

# 파일 업로더
uploaded_file = st.file_uploader("Chip Plate Export 파일 업로드 (CSV 포맷)", type=['csv'])

if uploaded_file:
    try:
        # 데이터 파일 읽기
        data_df = pd.read_csv(uploaded_file)
        
        # 파일명에서 확장자를 제외한 순수 이름 추출 (ChipPlateID)
        # 예: "Experiment_001.csv" -> "Experiment_001"
        chip_plate_id = os.path.splitext(uploaded_file.name)[0]
        
        # 원본 데이터에 필수 컬럼이 있는지 확인
        required_cols = ['SamplePlate', 'Well', 'Product ID', 'ChipPlate', 'Well.1', 'MG ID']
        missing_cols = [col for col in required_cols if col not in data_df.columns]
        
        if missing_cols:
            st.error(f"❌ 업로드한 파일에 다음 필수 컬럼이 없습니다: {', '.join(missing_cols)}")
        else:
            # 새로운 템플릿 구조로 DataFrame 생성 및 StoreTubeID 조합
            converted_result_df = pd.DataFrame({
                'SamplePlate': data_df['SamplePlate'],
                'SamplePosition': data_df['Well'],
                'Product ID': data_df['Product ID'],
                'ChipPlateID': data_df['ChipPlate'],
                'ChipPlatePosition': data_df['Well.1'],
                'StoreTubeID': chip_plate_id + '_' + data_df['Well.1'].astype(str), # 파일명 + "_" + Well.1
                'MG ID': data_df['MG ID'],  
            })
            
            st.success("✅ 파일 변환이 완료되었습니다!")
            
            # 결과 미리보기
            st.dataframe(converted_result_df)
            
            # 엑셀(CSV) 다운로드 시 한글 깨짐을 방지하기 위해 utf-8-sig 인코딩 사용
            csv_data = converted_result_df.to_csv(index=False).encode('utf-8-sig')
            
            # 파일 다운로드 버튼 생성
            st.download_button(
                label="📥 변환된 CSV 파일 다운로드",
                data=csv_data,
                file_name=f"Converted_{uploaded_file.name}",
                mime="text/csv"
            )
            
    except Exception as e:
        st.error(f"❌ 데이터 처리 중 오류가 발생했습니다: {e}")
