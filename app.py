import streamlit as st
from google import genai
from google.genai import types
import tempfile
import os
import time

st.set_page_config(
    page_title="PDF PO & Quotation Auditor", 
    page_icon="📄", 
    layout="wide"
)

st.title("📄 ระบบตรวจสอบ (PO & Quotation)")
st.caption("เปรียบเทียบไฟล์ Quotation (File A) กับ PO (File B) แบบละเอียดครบถ้วนทุกหน้า ยึดใบตั้งต้นเป็นหลัก 100%")

api_key = st.text_input("กรอก Gemini API Key ของคุณที่นี่", type="password", help="วาง API Key ที่ได้มาจาก Google AI Studio ตรงนี้")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. ไฟล์ตั้งต้น (Baseline - Quotation)")
    file_a = st.file_uploader("เลือกไฟล์ PDF Quotation", type=["pdf"], key="file_quotation")

with col2:
    st.subheader("2. ไฟล์ที่ต้องการตรวจ (To Check - PO)")
    file_b = st.file_uploader("เลือกไฟล์ PDF PO", type=["pdf"], key="file_po")

def upload_to_gemini(client, uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    g_file = client.files.upload(file=tmp_path)
    while g_file.state.name == "PROCESSING":
        time.sleep(2)
        g_file = client.files.get(name=g_file.name)
        
    os.unlink(tmp_path)
    return g_file

st.divider()

if st.button("🚀 เริ่มตรวจสอบและเปรียบเทียบไฟล์ PDF ทุกหน้า", type="primary", use_container_width=True):
    if not api_key:
        st.error("กรุณากรอก Gemini API Key ในช่องด้านบนก่อนครับ")
    elif not file_a or not file_b:
        st.error("กรุณาอัปโหลดไฟล์ PDF ให้ครบทั้ง 2 ไฟล์ครับ")
    else:
        status_box = st.status("กำลังประมวลผลตรวจสอบทุกหน้า ทุกแผ่น...", expanded=True)
        uploaded_files = []
        
        try:
            client = genai.Client(api_key=api_key)
            
            status_box.write("กำลังส่งไฟล์เข้าสู่ระบบวิเคราะห์ AI...")
            g_a = upload_to_gemini(client, file_a)
            uploaded_files.append(g_a.name)
            
            g_b = upload_to_gemini(client, file_b)
            uploaded_files.append(g_b.name)
            
            status_box.write("AI กำลังสแกนตรวจเทียบเอกสารทุกหน้าแบบละเอียด 100%...")
            
            prompt = '''จงเปรียบเทียบเอกสาร B (ไฟล์ตรวจสอบ PO) กับ เอกสาร A (ไฟล์ตั้งต้น Quotation) อย่างละเอียดถี่ถ้วน "ทุกหน้า ทุกแผ่นแบบครบถ้วน 100%"

หลักการตรวจสอบ:
1. ตรวจสอบทีละหน้าอย่างเป็นระบบ (ตั้งแต่หน้าแรกจนถึงหน้าสุดท้ายของเอกสาร) ห้ามข้ามหน้าใดๆ ทั้งสิ้น
2. ยึดข้อมูลในเอกสาร A (Quotation) เป็นความถูกต้องหลัก 100% (Description, รหัสสินค้า, ราคา, จำนวน)
3. หากเอกสาร B มีการย่อข้อความ แต่ทำให้สาระสำคัญ สเปก รหัส หรือตัวเลขคลาดเคลื่อน/ตกหล่น ให้ถือว่าผิดพลาด
4. ระบุเลขหน้า (page) ให้ตรงกับหน้าจริงในเอกสาร B ที่พบความผิดพลาด

รูปแบบรายงานสรุป:
### ตารางเปรียบเทียบและผลการตรวจสอบ (ทุกหน้า)
แสดงผลเป็นตาราง Markdown 5 คอลัมน์หลัก:
1. หน้าที่พบ (Page)
2. รายการ / รหัสสินค้า
3. รายละเอียดใน A (ถูกต้อง)
4. รายละเอียดใน B (ที่ผิด/ตกหล่น)
5. ผลการตรวจสอบ / สิ่งที่ต้องแก้ไข

### สรุปภาพรวมทุกหน้า
สรุปภาพรวมการตรวจสอบทุกแผ่น'''
            
            max_retries = 5
            retry_delay = 5
            response = None
            success = False
            
            config = types.GenerateContentConfig(
                max_output_tokens=8192,
                temperature=0.1
            )
            
            for attempt in range(max_retries):
                try:
                    status_box.write(f"กำลังวิเคราะห์ข้อมูลทุกหน้า (พยายามครั้งที่ {attempt+1}/{max_retries})...")
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=[g_a, g_b, prompt],
                        config=config
                    )
                    success = True
                    break
                except Exception as api_err:
                    if ("503" in str(api_err) or "UNAVAILABLE" in str(api_err)) and attempt < max_retries - 1:
                        status_box.warning(f"เซิร์ฟเวอร์หนาแน่น กำลังลองใหม่ในอีก {retry_delay} วินาที...")
                        time.sleep(retry_delay)
                        retry_delay += 3
                    else:
                        raise api_err
            
            if not success or not response:
                raise Exception("เซิร์ฟเวอร์หนาแน่นเกินไป โปรดลองกดปุ่มเริ่มตรวจสอบใหม่อีกครั้ง")
            
            clean_output = response.text.replace("<br>", " ").replace("<br/>", " ").replace("<BR>", " ")
            
            status_box.update(label="ตรวจสอบและวิเคราะห์เอกสารเรียบร้อยสมบูรณ์!", state="complete", expanded=False)
            
            st.markdown(clean_output)
            
            st.divider()
            st.download_button(
                label="ดาวน์โหลดรายงานผลการตรวจสอบ (.txt)",
                data=clean_output,
                file_name="po_audit_report.txt",
                mime="text/plain"
            )

        except Exception as e:
            status_box.update(label="เกิดข้อผิดพลาดในการประมวลผล", state="error", expanded=True)
            st.error(f"รายละเอียด: {str(e)}")
            
        finally:
            if uploaded_files and 'client' in locals():
                for name in uploaded_files:
                    try:
                        client.files.delete(name=name)
                    except:
                        pass
