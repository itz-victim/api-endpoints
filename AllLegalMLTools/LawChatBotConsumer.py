from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.chains import ConversationalRetrievalChain

from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
import os
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from dotenv import load_dotenv
load_dotenv()
import logging
from asgiref.sync import sync_to_async
from langchain.schema import AIMessage, HumanMessage, SystemMessage

OPENAI_API_KEY = os.environ['AZURE_OPENAI_API_KEY']
AZURE_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
AZURE_ENDPOINT1 = os.environ['AZURE_OPENAI_ENDPOINT1']
OPENAI_VERSION = os.environ['OPENAI_API_VERSION']
OPENAI_API_KEY1 = os.environ['AZURE_OPENAI_API_KEY1']

logger = logging.getLogger(__name__)

class LawChatBotConsumer(AsyncWebsocketConsumer):

    # For connection and session memory initialization
    async def connect(self):
        await self.accept()
        self.memory_key = "chat_history"
        self.memory = ConversationBufferWindowMemory(k=2, memory_key=self.memory_key, return_messages=True)

    # For disconnection and session cleanup if needed
    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with close code: {close_code}")
        # Add any cleanup logic here

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.default_memory = ConversationBufferWindowMemory(k=2, memory_key="chat_history", return_messages=True)

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

    def get_memory(self):
        session_memory = self.scope["session"].get(self.memory_key)
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

    def save_memory(self, memory):
        try:
            serialized_messages = [self.serialize_message(msg) for msg in memory.chat_memory.messages]
            self.scope["session"][self.memory_key] = serialized_messages
            self.scope["session"].modified = True
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

    # Handling WebSocket data or queries from the client
    async def receive(self, text_data):
        data = json.loads(text_data)
        query = data.get('query')

        response = await self.generate_response(query)

        await self.send(text_data=json.dumps({
            'response': response
        }))

    # For generating the response using FAISS and LLM (asynchronously)
    async def generate_response(self, query):
        # Asynchronous embedding model initialization
        embedding_model = AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-3-large",
            openai_api_version="2024-05-01-preview",
        )

        # Load FAISS asynchronously
        db = await sync_to_async(FAISS.load_local)("AllLegalMLTools/ipc_vector_db_open", embedding_model, allow_dangerous_deserialization=True)
        db_retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})

        prompt = ChatPromptTemplate.from_messages([
            ("system", "This is a chat template and As a legal chat bot specializing in Indian Penal Code queries, your primary objective is to provide accurate and concise information based on the user's questions. Do not generate your own questions and answers. You will adhere strictly to the instructions provided, offering relevant context from the knowledge base while avoiding unnecessary details. Your responses will be brief, to the point, and in compliance with the established format. If a question falls outside the given context, you will refrain from utilizing the chat history and instead rely on your own knowledge base to generate an appropriate response. You will prioritize the user's query and refrain from posing additional questions. The aim is to deliver professional, precise, and contextually relevant information pertaining to the Indian Penal Code. Answers should be based on context:{context}"),
            ("human", "{question}")
        ])

        # Asynchronous LLM model initialization
        llm = AzureChatOpenAI(
            model="gpt-4o",
            openai_api_version="2024-05-01-preview",
            azure_endpoint="https://tecosys.openai.azure.com/",
            api_key="your-api-key-here"
        )

        # Retrieve chat history from session
        last_chat_history = self.get_memory()
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

        # Generate the answer (call the LLM)
        answer = await sync_to_async(qa.invoke)({"question": query})

        # Save the new memory state to the session
        self.save_memory(last_chat_history)

        return answer
