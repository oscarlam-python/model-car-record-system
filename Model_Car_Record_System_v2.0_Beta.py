import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Model Car Record System", layout="wide")
st.title("Model Car Record System")

DB_NAME = "model_cars.db"

# ====================== 資料庫初始化 ======================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_cars (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            car_brand TEXT,
            model TEXT,
            scale TEXT,
            car_plate TEXT,
            car_number TEXT,
            purchase_date TEXT,
            value REAL,
            notes TEXT,
            product_id TEXT,
            product_web_link TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ====================== 資料庫操作 ======================
def get_all_cars():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM model_cars ORDER BY id", conn)
    conn.close()
    return df

def get_next_available_id():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM model_cars")
    max_id = cursor.fetchone()[0]
    if max_id is None:
        return 1
    cursor.execute("""
        SELECT id + 1 FROM model_cars 
        WHERE id + 1 NOT IN (SELECT id FROM model_cars) 
        AND id + 1 <= ? 
        ORDER BY id + 1 LIMIT 1
    """, (max_id + 1,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else max_id + 1

def save_car(data, car_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if car_id:
        cursor.execute('''
            UPDATE model_cars SET 
                brand=?, car_brand=?, model=?, scale=?, car_plate=?, car_number=?,
                purchase_date=?, value=?, notes=?, product_id=?, product_web_link=?
            WHERE id=?
        ''', (*data, car_id))
    else:
        next_id = get_next_available_id()
        cursor.execute('''
            INSERT INTO model_cars 
            (id, brand, car_brand, model, scale, car_plate, car_number, 
             purchase_date, value, notes, product_id, product_web_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, *data))
    conn.commit()
    conn.close()

def delete_car(car_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM model_cars WHERE id = ?", (car_id,))
    conn.commit()
    conn.close()

# ====================== 主介面 ======================
tab1, tab2, tab3 = st.tabs(["📋 資料列表", "➕ 新增 / 編輯", "📊 Excel 工具"])

with tab1:
    st.subheader("收藏列表")
    df = get_all_cars()
    keyword = st.text_input("🔍 搜尋", "")
    if keyword:
        df = df[df.apply(lambda row: keyword.lower() in str(row).lower(), axis=1)]
    st.dataframe(df, use_container_width=True, hide_index=True)

    selected_ids = st.multiselect("選擇要刪除的 ID", options=df['id'].tolist() if not df.empty else [])
    if st.button("🗑️ 刪除選取的資料"):
        if selected_ids:
            for cid in selected_ids:
                delete_car(cid)
            st.success(f"已刪除 {len(selected_ids)} 筆資料")
            st.rerun()

with tab2:
    st.subheader("新增 / 編輯模型車")
    cars = get_all_cars()
    edit_options = [None] + list(cars['id']) if not cars.empty else [None]
    selected_id = st.selectbox(
        "選擇要編輯的記錄（留空則為新增）", 
        options=edit_options,
        format_func=lambda x: f"ID {x} - 編輯" if x else "新增新記錄"
    )

    with st.form("car_form"):
        col1, col2 = st.columns(2)
        with col1:
            brand = st.selectbox("品牌 *", ["Tiny", "MiniGT", "Tomica", "Tomica Premium", "BMC", "DCT", "拓意"])
            car_brand = st.text_input("車廠 *")
            model = st.text_input("型號")
            scale = st.selectbox("比例", ["1:64","1:43","1:32","1:18","1:10","1:8","1:76","1:110"])
            car_plate = st.text_input("車牌")
            car_number = st.text_input("編號")
        with col2:
            purchase_date = st.text_input("購買日期 (YYYY-MM-DD)")
            value = st.number_input("金額 (HKD)", min_value=0.0, step=10.0)
            product_id = st.text_input("產品編號")
            product_web_link = st.text_input("產品連結")
            notes = st.text_area("備註", height=120)

        if st.form_submit_button("💾 儲存記錄"):
            data = (brand, car_brand, model, scale, car_plate, car_number,
                    purchase_date, value, notes, product_id, product_web_link)
            save_car(data, selected_id)
            st.success("✅ 儲存成功！")
            st.rerun()

with tab3:
    st.subheader("📊 Excel 工具")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("從 Excel 匯入")
        uploaded_file = st.file_uploader("上傳 Excel 檔案 (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.success("✅ 檔案讀取成功！預覽前 10 筆：")
                st.dataframe(df.head(10))
                
                if st.button("確認匯入資料到資料庫"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    success = 0
                    skipped = 0
                    
                    for _, row in df.iterrows():
                        try:
                            cursor.execute('''
                                INSERT INTO model_cars 
                                (brand, car_brand, model, scale, car_plate, car_number, purchase_date, 
                                 value, notes, product_id, product_web_link)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                str(row.get('品牌', '')).strip(),
                                str(row.get('車廠', '')).strip(),
                                str(row.get('型號', '')).strip(),
                                str(row.get('比例', '')).strip(),
                                str(row.get('車牌', '')).strip(),
                                str(row.get('編號', '')).strip(),
                                str(row.get('購買日期', '')).strip(),
                                float(row.get('金額 (HKD)')) if pd.notna(row.get('金額 (HKD)')) else None,
                                str(row.get('備註', '')).strip(),
                                str(row.get('產品編號', '')).strip(),
                                str(row.get('產品連結', '')).strip()
                            ))
                            success += 1
                        except:
                            skipped += 1
                    
                    conn.commit()
                    conn.close()
                    st.success(f"✅ 匯入完成！成功 {success} 筆，跳過 {skipped} 筆")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 讀取失敗：{str(e)}")
                st.info("💡 建議：請確保 Excel 第一列欄位名稱正確（品牌、車廠、型號、比例、車牌、編號、購買日期、金額 (HKD)、備註、產品編號、產品連結）")

    with col2:
        st.write("匯出資料")
        if st.button("📤 匯出目前所有資料"):
            df = get_all_cars()
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下載 CSV 檔案",
                data=csv,
                file_name=f"MCRS_Record_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
                mime="text/csv"
            )

st.caption("Model Car Record System | By Oscar Lam | 2026/03/30 | v2.0 | Streamlit 網頁版")
