import os
from dotenv import load_dotenv
from io import BytesIO
import chainlit as cl
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Embedding model
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# LLM model from ChatGroq
llm = ChatGroq(
    temperature=0.5,
    model_name="llama3-70b-8192",
    groq_api_key=GROQ_API_KEY
)

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

@cl.on_chat_start
async def on_chat_start():

    elements = [
    cl.Image(name="image_my", display="inline", path= r'D:\1. INDIUM\Project\DATA\project_2_data\indiumsoftware_logo.jpeg')
    ]
    await cl.Message(
        content="#### Welcome to Indium Pdf Chat!\nUpload a PDF to get started."
    ).send()

    files = await cl.AskFileMessage(
        content="Upload your PDF file",
        accept=["application/pdf"],
        max_size_mb=10
    ).send()

    file = files[0]
    with open(file.path, "rb") as f:
        pdf_reader = PyPDF2.PdfReader(f)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    chunks = text_splitter.split_text(text)
    texts = [chunk for chunk in chunks]

    # Create FAISS vector store
    vector_store = FAISS.from_texts(texts, embedding_model)

    # saving vector store
    cl.user_session.set("vector_store", vector_store)

    await cl.Message(content="Now I am ready, Ask questions!").send()

@cl.on_message
async def on_message(message: cl.Message):
    vector_store = cl.user_session.get("vector_store")
    if not vector_store:
        await cl.Message(content="Please upload a PDF first.").send()
        return

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever
    )

    response = qa_chain(message.content)
    answer = response["result"]

    await cl.Message(content=f"**Answer:** {answer}").send()
