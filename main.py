from fastapi import FastAPI, Query
import os
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import nltk
from transformers import pipeline
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

 
# Download necessary NLTK data
nltk.download('punkt')

app = FastAPI()

UPLOAD_DIR = "uploads"
CHROMA_DB_DIR = "chroma_db"

# Ensure necessary directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="pdf_docs")

# Function to process PDFs with LangChain
def process_pdf_with_langchain(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    return [chunk.page_content for chunk in chunks]

# Handle multiple PDFs from a folder
@app.post("/upload_folder/")
async def upload_folder(folder_path: str = Query(..., description="Path to the folder containing PDFs")):
    if not os.path.exists(folder_path):
        return {"error": "Folder not found"}
    
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    if not pdf_files:
        return {"error": "No PDFs found in the specified folder"}

    for pdf_file in pdf_files:
        file_path = os.path.join(folder_path, pdf_file)
        chunks = process_pdf_with_langchain(file_path)

        if not chunks:
            continue  # Skip PDFs with no text

        # Store chunks in ChromaDB
        for i, chunk in enumerate(chunks):
            doc_id = f"{pdf_file}_{i}"
            collection.add(
                documents=[chunk],
                metadatas=[{"filename": pdf_file, "chunk_id": i}],
                ids=[doc_id]
            )

    return {"message": f"Processed {len(pdf_files)} PDFs successfully", "files": pdf_files}

# DELETE endpoint to remove stored PDFs
@app.delete("/delete/{filename}")
async def delete_pdf(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Delete file if it exists
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        return {"error": "File not found"}

    # Delete related entries from ChromaDB
    all_docs = collection.get()
    doc_ids_to_delete = [doc_id for doc_id in all_docs["ids"] if filename in doc_id]

    if doc_ids_to_delete:
        collection.delete(ids=doc_ids_to_delete)

    return {"message": f"Deleted {filename} and its indexed data"}

# Query endpoint
@app.get("/query/")
async def query_pdf(question: str = Query(..., description="Enter your query")):
    # Retrieve stored text chunks
    all_docs = collection.get()

    if not all_docs["documents"]:
        return {"response": "No documents found in the database."}

    # Combine all text chunks into a single context
    context_text = " ".join(all_docs["documents"])

    # Use Gemini API for chat completion
    try:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(f"Context: {context_text}\n\nQuestion: {question}\n\nAnswer:")
        generated_response = response.text if response.text else "Sorry, I couldn't find relevant information."
    except Exception as e:
        generated_response = f"Error: {str(e)}"

    return {"response": generated_response}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)




