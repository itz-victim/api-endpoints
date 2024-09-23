import streamlit as st
import fitz  
import faiss
import tiktoken
import requests
import io
import numpy as np
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.environ['AZURE_OPENAI_API_KEY']
AZURE_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
AZURE_ENDPOINT1 = os.environ['AZURE_OPENAI_ENDPOINT1']
OPENAI_VERSION = os.environ['OPENAI_API_VERSION']
OPENAI_API_KEY1 = os.environ['AZURE_OPENAI_API_KEY1']

client = AzureOpenAI(
    api_version=OPENAI_VERSION,
    azure_endpoint=AZURE_ENDPOINT1,
    api_key=OPENAI_API_KEY1,
)

def extract_text_from_pdf(pdf_file):
    if pdf_file is None:
        raise ValueError("No PDF file provided")
    document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    if document.page_count == 0:
        raise ValueError("The provided PDF file is empty")
    text = ""
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        text += page.get_text()
    return text

def clean_text(text):
    return text.replace('\n', ' ').replace('\r', ' ').strip()

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def split_text_into_token_chunks(text, max_tokens, encoding_name="cl100k_base"):
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i+max_tokens]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
    return chunks

def generate_embeddings(texts):
    embeddings = []
    max_token_length = 8191
    for text in texts:
        num_tokens = num_tokens_from_string(text, "cl100k_base")
        if num_tokens > max_token_length:
            sub_texts = split_text_into_token_chunks(text, max_token_length)
            for sub_text in sub_texts:
                response = client.embeddings.create(input=sub_text, model="text-embedding-3-large").data[0].embedding
                embeddings.append(response)
        else:
            response = client.embeddings.create(input=text, model="text-embedding-3-large").data[0].embedding
            embeddings.append(response)
    return np.array(embeddings)

def index_embeddings(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def retrieve_similar_chunks(index, query_embedding, texts, top_k=5):
    distances, indices = index.search(np.array([query_embedding]), top_k)
    return [texts[i] for i in indices[0]]

def generate_summary(chunks):
    max_chunk_length = 8191 
    truncated_chunks = []
    current_length = 0

    for chunk in chunks:
        chunk_length = num_tokens_from_string(chunk, "cl100k_base")
        if current_length + chunk_length > max_chunk_length:
            break
        truncated_chunks.append(chunk)
        current_length += chunk_length

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "First of all write the Title of the case first. Summarize the following text into the specified sections: Facts, Issues, Decision (Holding), Reasoning (Rationale), Disposition, Precedent, and Note. Provide at least two points for each section. If any section lacks sufficient information, provide a brief summary for that section. Ensure the output is formatted as a list of points."},
            {"role": "user", "content": ' '.join(truncated_chunks)},
            {"role": "user", "content": """
                1. **Facts**: 
                   - This section provides the background and key events that led to the legal dispute. 
                   - It sets the stage by explaining the who, what, when, where, and why of the case.
                2. **Issues**: 
                   - This section identifies the specific legal questions or points of contention that the court needs to resolve. 
                   - Clearly outlining the issues helps to focus on the critical legal questions at hand.
                3. **Decision (Holding)**: 
                   - This section provides the court's ruling on the issues presented. 
                   - It includes the outcome of the case and the key legal principles or rules established by the court’s decision.
                4. **Reasoning (Rationale)**: 
                   - This section explains the court’s rationale for its decision, including the legal principles, statutes, precedents, and logical arguments the court used to arrive at its conclusion.
                   - Provide details on how the court interpreted the law and applied it to the facts of the case.
                5. **Disposition**: 
                   - This section states the final resolution of the case, including any orders or instructions from the court. 
                   - It indicates what happens next, such as whether the case is dismissed, remanded, or if any specific actions are required by the parties.
                6. **Precedent**: 
                   - This section mentions previous legal cases or decisions that the court relied upon or referenced in its reasoning. 
                   - Understanding which precedents were considered can provide insight into the legal context and how the court interpreted similar issues in the past.
                7. **Note**: 
                   - This section may include additional observations, clarifications, or pertinent information that does not fit neatly into the other sections. 
                   - It might highlight unique aspects of the case, procedural issues, or other relevant details.
            """}
        ]
    )
    return response.choices[0].message.content

def download_pdf_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return io.BytesIO(response.content)
    else:
        raise ValueError("Unable to download PDF from the provided URL")

if __name__ == "__main__":
    if st.button("Home"):
        st.session_state.page = "home"
    
    st.title("Court Case Summariser")
    
    pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    pdf_url = st.text_input("Or enter the URL of a PDF file")

    if pdf_file is not None or pdf_url:
        if pdf_file:
            text = extract_text_from_pdf(pdf_file)
        else:
            pdf_stream = download_pdf_from_url(pdf_url)
            text = extract_text_from_pdf(pdf_stream)
        
        cleaned_text = clean_text(text)
        chunks = split_text_into_token_chunks(cleaned_text, 4000)

        try:
            embeddings = generate_embeddings(chunks)
            index = index_embeddings(embeddings)

            query_embedding = generate_embeddings([cleaned_text[:8191]])[0]  
            similar_chunks = retrieve_similar_chunks(index, query_embedding, chunks)

            summary = generate_summary(similar_chunks)
    #below are the  genarated ans needs to be send back through api endpoint
            st.write("Summary:")
            st.write(summary)
        except ValueError as e:
            st.error(f"Error: {e}")
