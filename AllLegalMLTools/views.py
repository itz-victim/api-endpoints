import os
import pandas as pd
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage
import logging
from dotenv import load_dotenv
load_dotenv()

from .case_summariser import extract_text_from_pdf, clean_text, split_text_into_token_chunks, generate_embeddings, index_embeddings, generate_summary, retrieve_similar_chunks, download_pdf_from_url
from rest_framework.permissions import AllowAny


logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ['AZURE_OPENAI_API_KEY']
AZURE_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
AZURE_ENDPOINT1 = os.environ['AZURE_OPENAI_ENDPOINT1']
OPENAI_VERSION = os.environ['OPENAI_API_VERSION']
OPENAI_API_KEY1 = os.environ['AZURE_OPENAI_API_KEY1']



# Below section is for case summarizer
class UploadCaseDocumentOrURLView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format = None):
        caseDocument = request.FILES.get('pdf_file')
        caseURL = request.data.get('url')

        if caseDocument or caseURL:
            if caseDocument:
                text = extract_text_from_pdf(caseDocument)
            else:
                caseURLPdf_stream = download_pdf_from_url(caseURL)
                text = extract_text_from_pdf(caseURLPdf_stream)

            cleaned_text = clean_text(text)
            chunks = split_text_into_token_chunks(cleaned_text, 4000)

            try:
                embeddings = generate_embeddings(chunks)
                index = index_embeddings(embeddings)

                query_embedding = generate_embeddings([cleaned_text[:8191]])[0]  
                similar_chunks = retrieve_similar_chunks(index, query_embedding, chunks)

                summary = generate_summary(similar_chunks)

                # here we need to return generated summary to frontend through api endpoint
                return Response({'summary': summary}, status=status.HTTP_200_OK)
            
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            return Response({'error': 'Invalid file type and void url'})
        
# Below classes both together is for handling case search and generating summary functionality
class CaseSearchView(APIView):
    # in development phase it is made that all can access this class view but before production make sure to change
    # AllowAny to IsAuthenticated or other built-in classes
    permission_classes = [AllowAny]      

    def post(self, request, format=None):
        case_search_query = request.data.get('search_query')
        file_path = os.path.join(settings.BASE_DIR, 'AllLegalMLTools', 'updated_merged_dataset.csv')
        merged_df = pd.read_csv(file_path)

        if case_search_query:
            case_search_query = case_search_query.lower()
            results = merged_df[merged_df['details'].str.contains(case_search_query, na=False)]

            if results.empty:
                return Response({'message': f"No results found for '{case_search_query}'"}, status=status.HTTP_200_OK)

            response_data = [
                {
                    'case_title': row['Case Title'],
                    'case_no': row['Case No'],
                    'pdf_link': row['PDF Link'],
                    'index' : idx
                }
                for idx, row in results.iterrows()
            ]

            return Response(response_data, status=status.HTTP_200_OK)

        else:
            return Response({'error': 'Invalid query'}, status=status.HTTP_400_BAD_REQUEST)
        
class CaseSummaryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format = None):
        case_index = request.data.get('index')
        file_path = os.path.join(settings.BASE_DIR, 'AllLegalMLTools', 'updated_merged_dataset.csv')
        merged_df = pd.read_csv(file_path)

        if case_index is not None:
            try:
                case_index = int(case_index)
                results = merged_df.iloc[case_index]

                pdf_url = results['PDF Link']
                response_data = []
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
                    response_data.append({
                        'Case Title': results['Case Title'],
                        'Case No': results['Case No'],
                        'Judges': results['Judges'],
                        'Decision Date': results['Decision Date_left'],
                        'Disposal Nature': results['Disposal Nature'],
                        'PDF Link': results['PDF Link'],
                        'Summary': summary
                    })
                    return Response(response_data, )
                except Exception as e:
                    return Response({'error': f"Failed to process:'{str(e)}'"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except Exception as e:
                return Response({'error': f"Case not found"}, status=status.HTTP_404_NOT_FOUND)
            
        else:
            return Response({'error': 'case_index is null'}, status=status.HTTP_400_BAD_REQUEST)
        
class LawChatBotView(APIView):
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.memory_key = "chat_history"
        self.default_memory = ConversationBufferWindowMemory(k=2, memory_key=self.memory_key, return_messages=True)

    def serialize_message(self, message):
        """
        Converts a message object to a serializable dictionary.
        """
        if isinstance(message, (AIMessage, HumanMessage, SystemMessage)):
            return {"type": message.type, "content": message.content}
        return str(message)

    def deserialize_message(self, message_dict):
        """
        Converts a dictionary back to a message object.
        """
        type = message_dict.get("type")
        content = message_dict.get("content")
        
        if type == "user":
            return HumanMessage(content=content)
        elif type == "assistant":
            return AIMessage(content=content)
        elif type == "system":
            return SystemMessage(content=content)
        return None

    def get_memory(self, request):
        session_memory = request.session.get(self.memory_key)
        if session_memory:
            memory = ConversationBufferWindowMemory(k=2, memory_key=self.memory_key, return_messages=True)
            try:
                deserialized_messages = [self.deserialize_message(msg) for msg in session_memory]
                memory.chat_memory.messages = deserialized_messages
            except Exception as e:
                logger.error(f"Error deserializing messages: {e}")
                return self.default_memory
            return memory
        return self.default_memory

    def save_memory(self, request, memory):
        try:
            serialized_messages = [self.serialize_message(msg) for msg in memory.chat_memory.messages]
            request.session[self.memory_key] = serialized_messages
            request.session.modified = True
        except Exception as e:
            logger.error(f"Error serializing messages: {e}")

    def validate_chat_history(self, messages):
        valid_messages = []
        for msg in messages:
            if isinstance(msg, (AIMessage, HumanMessage, SystemMessage)):
                valid_messages.append(msg)
            else:
                logger.warning(f"Invalid message found: {msg}")
        return valid_messages

    def generate_response(self, query, request):
        embedding_model = AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-3-large",
            openai_api_version=OPENAI_VERSION,
        )
        db = FAISS.load_local("AllLegalMLTools/ipc_vector_db_open", embedding_model, allow_dangerous_deserialization=True)
        db_retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})

        prompt = ChatPromptTemplate.from_messages([
            ("system", "This is a chat template and As a legal chat bot specializing in Indian Penal Code queries, your primary objective is to provide accurate and concise information based on the user's questions. Do not generate your own questions and answers. You will adhere strictly to the instructions provided, offering relevant context from the knowledge base while avoiding unnecessary details. Your responses will be brief, to the point, and in compliance with the established format. If a question falls outside the given context, you will refrain from utilizing the chat history and instead rely on your own knowledge base to generate an appropriate response. You will prioritize the user's query and refrain from posing additional questions. The aim is to deliver professional, precise, and contextually relevant information pertaining to the Indian Penal Code. Answers should be based on context:{context}"),
            ("human", "{question}")
        ])

        llm = AzureChatOpenAI(
            model="gpt-4o",
            openai_api_version="2024-05-01-preview",
            azure_endpoint="https://tecosys.openai.azure.com/",
            api_key="e36e1f09a3d14e19b48078b385b9927d"
        )

        last_chat_history = self.get_memory(request)
        valid_chat_history = self.validate_chat_history(last_chat_history.chat_memory.messages)

        qa = ConversationalRetrievalChain.from_llm(
            llm=llm,
            memory=ConversationBufferWindowMemory(
                k=2,
                memory_key=self.memory_key,
                return_messages=True,
                messages=valid_chat_history
            ),
            retriever=db_retriever,
            combine_docs_chain_kwargs={'prompt': prompt}
        )

        answer = qa.invoke({"question": query})

        # Update memory with new messages
        self.save_memory(request, last_chat_history)

        return answer

    def post(self, request, format=None):
        query = request.data.get('query')
        answer = self.generate_response(query, request)
        # Serialize the answer if needed before returning
        if answer is not None:
            # try:
            #     serialized_answer = self.serialize_message(answer)

            #     return Response({
            #         "response": serialized_answer,
            #     })
            # except Exception as e:
            #     return Response({"error": f"Server is facing serialization issue:'{str(e)}'"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
            # If `answer` is a dictionary, send it directly as part of the response
            # Ensure that `answer` contains keys like 'question', 'chat_history', 'answer'
                if isinstance(answer, str):
                    answer = eval(answer)  # Convert string representation of dict to actual dict
                
                return Response({
                    "question": answer.get('question'),
                    "chat_history": answer.get('chat_history', []),
                    "answer": answer.get('answer')
                })
            except Exception as e:
                return Response({"error": f"Server is facing serialization issue: '{str(e)}'"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"error": "LLM engine issue"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)