import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re

st.set_page_config(page_title="Plate Position 시각화", layout="wide")

st.title("🧪 Plate Position 시각화")
st.markdown("---")

file = st.file_uploader("Chip work data 엑셀 업로드", type=['xlsx'])
spl_input = st.text_area("SPL ID 입력 (한 줄에 하나씩)")

if file and spl_input:
    df = pd.read_excel(file, sheet_name='Sheet')
    spl_list = [s.strip() for s in spl_input.split('\n') if s.strip()]
    
    # SPL ID 기준 데이터 필터링
    filtered = df[df['SPL.'].isin(spl_list)]
    
    if not filtered.empty:
        st.success(f"✅ 총 {len(filtered)}개의 샘플을 찾았습니다.")
        
        pos_col = next((c for c in df.columns if 'Pos' in str(c) or 'Well' in str(c)), None)
        
        if not pos_col:
            st.error("엑셀 파일에서 위치(Position/Well) 컬럼을 찾을 수 없습니다.")
        else:
            # 96-well plate 기본 뼈대
            rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
            cols = [str(i) for i in range(1, 13)]
            
            plate_color = pd.DataFrame(np.zeros((8, 12)), index=rows, columns=cols)
            plate_text = pd.DataFrame(index=rows, columns=cols)
            
            # 1. 셀마다 1~96 고유 번호 부여 (세로 방향 우선 규칙 적용)
            # (A1=1, B1=2, C1=3 ... A2=9, B2=10)
            for c_idx, c in enumerate(cols):
                for r_idx, r in enumerate(rows):
                    cell_num = (c_idx * 8) + r_idx + 1
                    plate_text.at[r, c] = str(cell_num)
            
            # 2. 찾은 샘플 위치에 색상 및 SPL ID 추가
            for idx, row_data in filtered.iterrows():
                pos = str(row_data[pos_col]).strip().upper()
                
                match = re.match(r'([A-H])(\d+)', pos)
                if match:
                    r_letter = match.group(1)
                    c_num = match.group(2)
                    
                    if r_letter in rows and c_num in cols:
                        # 배경색 활성화
                        plate_color.at[r_letter, c_num] = 1 
                        
                        # 기존 번호 아래에 SPL ID 줄바꿈 추가
                        spl_id = str(row_data['SPL.'])
                        existing_text = plate_text.at[r_letter, c_num]
                        
                        # 중복으로 글자가 들어가는 것 방지
                        if spl_id not in existing_text:
                            plate_text.at[r_letter, c_num] = f"{existing_text}\n{spl_id}"

            # 3. 그래프 그리기
            fig, ax = plt.subplots(figsize=(14, 7))
            
            sns.heatmap(plate_color, 
                        annot=plate_text, 
                        fmt="", 
                        cmap="Blues", 
                        cbar=False, 
                        linewidths=1.5, 
                        linecolor='#E0E0E0', 
                        ax=ax,
                        annot_kws={"size": 9, "weight": "bold"}) # 글자 크기와 굵기 조정
            
            # X축 번호를 위로 이동
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position('top')
            plt.yticks(rotation=0, fontsize=12, fontweight='bold')
            plt.xticks(fontsize=12, fontweight='bold')
            
            st.pyplot(fig)
            
            st.markdown("### 📋 상세 데이터")
            st.dataframe(filtered)
            
    else:
        st.warning("⚠️ 일치하는 샘플이 없습니다.")