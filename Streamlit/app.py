import streamlit as st
import PyPDF2
import docx
import subprocess
import os

# Set the root directory based on your project structure
ROOT_DIR = os.path.join(os.path.dirname(__file__), '../..')  

# Function to process and index the uploaded file
def process_and_index(uploaded_file):
    # Create a temporary file path
    temp_file_path = os.path.join(ROOT_DIR, 'ragtest', 'temp_document.txt')

    # Write the uploaded file content to the temp file
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        text = '\n'.join([para.text for para in doc.paragraphs])
    elif uploaded_file.type == "text/plain":
        text = uploaded_file.getvalue().decode("utf-8")
    else:
        st.error("Unsupported file type. Please upload a PDF, Word, or text document.")
        return

    # Save text to the temporary file
    with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
        temp_file.write(text)

    # Index the document using Graphrag
    try:
        subprocess.run(["python", "-m", "graphrag.index", "--root", os.path.join(ROOT_DIR, 'ragtest')], check=True)
        st.success("Document indexed successfully!")
    except subprocess.CalledProcessError as e:
        st.error(f"Error indexing document: {e}")

# Streamlit UI
st.title("Document Uploader")
uploaded_file = st.file_uploader("Choose a PDF, Word, or text document", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    process_and_index(uploaded_file)
