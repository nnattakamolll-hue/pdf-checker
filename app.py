import streamlit as st
import pypdf
from google import genai

st.set_page_config(page_title="PDF Verifier", layout="wide")

st.title("🔍 ระบบอัปโหลดและตรวจสอบเอกสาร PDF ด้วย AI")
st.write("อัปโหลดไฟล์ PDF 2 ไฟล์เพื่อเปรียบเทียบเนื้อหาและตรวจสอบความถูกต้อง")

col1, col2 = st.columns(2)

with col1:
    st.subheader("ไฟล์ที่ 1 (ต้นฉบับ)")
    file1 = st.file_uploader("เลือกไฟล์ PDF ไฟล์ที่ 1", type=["pdf"], key="file1")

with col2:
    st.subheader("ไฟล์ที่ 2 (เอกสารที่ต้องการตรวจสอบ)")
    file2 = st.file_uploader("เลือกไฟล์ PDF ไฟล์ที่ 2", type=["pdf"], key="file2")

if file1 and file2:
    if st.button("🚀 เริ่มเปรียบเทียบและตรวจสอบข้อมูล", type="primary"):
        with st.spinner("กำลังอ่านและวิเคราะห์เอกสาร..."):
            try:
                reader1 = pypdf.PdfReader(file1)
                text1 = "".join([page.extract_text() for page in reader1.pages])

                reader2 = pypdf.PdfReader(file2)
                text2 = "".join([page.extract_text() for page in reader2.pages])

                api_key = st.secrets.get("GEMINI_API_KEY", "")
                
                # รองรับทั้งคีย์แบบ AQ (OAuth) และคีย์ปกติ
                if api_key.startswith("AQ"):
                    client = genai.Client(http_options={'api_version': 'v1alpha'}, vertexai=False)
                    client.api_client.api_key = None
                    client.api_client.default_headers = {"Authorization": f"Bearer {api_key}"}
                else:
                    client = genai.Client(api_key=api_key)

                prompt = f"""
คุณเป็นผู้ตรวจสอบเอกสารระดับมืออาชีพ กรุณาเปรียบเทียบข้อมูลในเอกสาร 2 ชุดนี้อย่างละเอียด:
1. สรุปภาพรวมว่าเนื้อหาตรงกัน ขัดแย้ง หรือมีข้อมูลผิดเพี้ยนไปจากเดิมหรือไม่
2. ระบุรายละเอียดจุดที่ตรงกันและจุดที่แตกต่างกันอย่างชัดเจน
3. หากมีข้อมูลตัวเลข ชื่อ หรือเงื่อนไขที่ไม่ตรงกัน ให้แจ้งเตือนทันที

--- เอกสารชุดที่ 1 ---
{text1}

--- เอกสารชุดที่ 2 ---
{text2}
"""

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )

                st.success("วิเคราะห์เสร็จเรียบร้อย!")
                st.markdown("### 📊 ผลการตรวจสอบ:")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
else:
    st.info("💡 กรุณาอัปโหลดไฟล์ PDF ทั้ง 2 ไฟล์ให้ครบถ้วนเพื่อเริ่มใช้งาน")
