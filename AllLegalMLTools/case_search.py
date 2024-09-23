import pandas as pd
import streamlit as st
from case_summariser import extract_text_from_pdf, clean_text, split_text_into_token_chunks, generate_embeddings, index_embeddings, retrieve_similar_chunks, generate_summary, download_pdf_from_url
import os
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import subprocess

#OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
merged_df = pd.read_csv('updated_merged_dataset.csv')

if __name__=="__main__":
    
    if st.button("Home"):
        st.session_state.page = "home"
        
    st.title("Case Search Interface")

    # this is the keywords that needs to be given from frontend through api endpoints
    keyword = st.text_input("Enter keyword to search in details:")

    if keyword:
        keyword1 = keyword.lower()
        
        results = merged_df[merged_df['details'].str.contains(keyword1, na=False)]

        if not results.empty:
            st.write(f"Found {len(results)} results matching '{keyword}':")
            for idx, row in results.iterrows():
                st.markdown("---")
                st.write(f"### Title: {row['Case Title']}")
                st.write(f"**Case No.:** {row['Case No']}")
                st.write(f"**Judges:** {row['Judges']}")
                st.write(f"**Decision Date:** {row['Decision Date_left']}")
                st.write(f"**Disposal Nature:** {row['Disposal Nature']}")
                st.markdown(f"[**PDF Link**]( {row['PDF Link']})")

                if st.button(f"Generate Summary for {row['Case Title']}", key=idx):
                    with st.spinner("Generating Summary for you ..."):
                        pdf_url = row['PDF Link']
                        try:
                            pdf_stream = download_pdf_from_url(pdf_url)
                            text = extract_text_from_pdf(pdf_stream)
                            cleaned_text = clean_text(text)
                            chunks = split_text_into_token_chunks(cleaned_text, 8191)

                            embeddings = generate_embeddings(chunks)
                            index = index_embeddings(embeddings)

                            query_embedding = generate_embeddings([cleaned_text[:8191]])[0] 
                            similar_chunks = retrieve_similar_chunks(index, query_embedding, chunks)

                            summary = generate_summary(similar_chunks)

    # below are the genarated answers need to be sent back from backend to frontend over an endpoint
                            st.write("Summary:")
                            st.header(f"**{row['Case Title']}**")
                            st.write(summary)
                        except ValueError as e:
                            st.error(f"Error: {e}")

        else:
            st.write(f"No results found for keyword '{keyword}'.")
