from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.chains import ConversationalRetrievalChain
import streamlit as st
import time
#from langchain_openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
import os
import streamlit as st
import subprocess

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.environ['AZURE_OPENAI_API_KEY']
AZURE_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
AZURE_ENDPOINT1 = os.environ['AZURE_OPENAI_ENDPOINT1']
OPENAI_VERSION = os.environ['OPENAI_API_VERSION']
OPENAI_API_KEY1 = os.environ['AZURE_OPENAI_API_KEY1']

if __name__=="__main__":

    if st.button("Home"):
        st.session_state.page = "home"
        
    st.header('Indian Penal Code : Chat with criminal laws')
    
    def reset_conversation():
        st.session_state.messages = []
        st.session_state.memory.clear()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferWindowMemory(k=2, memory_key="chat_history", return_messages=True)

    embedding_model = AzureOpenAIEmbeddings(
    azure_deployment="text-embedding-3-large",
    openai_api_version=OPENAI_VERSION,
    )
    try:
        db = FAISS.load_local("ipc_vector_db_open", embedding_model, allow_dangerous_deserialization=True)
    except AssertionError as e:
        st.error("Error loading FAISS index. Ensure the embedding model used for indexing matches the one used for querying.")
        raise e

    db_retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    prompt = ChatPromptTemplate.from_messages([
        ("system", "This is a chat template and As a legal chat bot specializing in Indian Penal Code queries, your primary objective is to provide accurate and concise information based on the user's questions. Do not generate your own questions and answers. You will adhere strictly to the instructions provided, offering relevant context from the knowledge base while avoiding unnecessary details. Your responses will be brief, to the point, and in compliance with the established format. If a question falls outside the given context, you will refrain from utilizing the chat history and instead rely on your own knowledge base to generate an appropriate response. You will prioritize the user's query and refrain from posing additional questions. The aim is to deliver professional, precise, and contextually relevant information pertaining to the Indian Penal Code. Answers should be based on context:{context}"),
        ("human", "{question}")
    ])
    
    llm = AzureChatOpenAI(
        openai_api_version=OPENAI_VERSION,
        azure_deployment="gpt-4o-mini",
        azure_endpoint=AZURE_ENDPOINT1,
        api_key=OPENAI_API_KEY1
    )
    # llm = ChatOpenAI(
    #     model="gpt-4o",
    #     temperature=0.3,
    #     max_tokens=1024,
    #     api_key=OPENAI_API_KEY
    # )

    qa = ConversationalRetrievalChain.from_llm(
        llm=llm,
        memory=st.session_state.memory,
        retriever=db_retriever,
        combine_docs_chain_kwargs={'prompt': prompt}
    )

    for message in st.session_state.messages:
        with st.chat_message(message.get("role")):
            st.write(message.get("content"))
# from below we need to look for user query fetching and handling
    input_prompt = st.chat_input("Ask any questions related to crime")

    if input_prompt:
        with st.chat_message("user"):
            st.write(input_prompt)

        st.session_state.messages.append({"role": "user", "content": input_prompt})

        with st.chat_message("assistant"):
            with st.spinner("Processing ..."):
                try:
                    result = qa.invoke({"question": input_prompt})
                except AssertionError as e:
                    st.error("Error during the retrieval process. Ensure the embedding dimensions match the FAISS index.")
                    raise e
                except ValueError as e:
                    st.error("Missing input keys. Ensure the input contains the required keys.")
                    raise e

                message_placeholder = st.empty()
                full_response = "According to cerina crime lawyer, \n\n\n"

                for chunk in result["answer"]:
                    full_response += chunk
                    time.sleep(0.02)
                    message_placeholder.markdown(full_response + " ▌")

        st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
        st.button('Reset Chat', on_click=reset_conversation)
