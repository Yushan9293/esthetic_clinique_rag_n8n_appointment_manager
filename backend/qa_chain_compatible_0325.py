from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.documents import Document
from openai import OpenAI
import json
import chromadb

# Session-based memory store
chat_histories = {}

# Build a retrieval-augmented QA chain with memory
def build_qa_chain(docs):
    # Step 1: Clean and validate document contents
    clean_docs = []
    for i, d in enumerate(docs):
        if not isinstance(d.page_content, str):
            print(f"❌ Skipping doc[{i}] - page_content is not a string: {type(d.page_content)}")
            continue
        if d.page_content.strip() == "":
            print(f"⚠️ Skipping doc[{i}] - empty string")
            continue
        clean_docs.append(d)
        print(f"✅ doc[{i}] OK: {d.page_content[:60]}...")

    if not clean_docs:
        raise ValueError("❌ No valid documents found to embed.")

    # Step 2: Create vectorstore with OpenAI embeddings
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        clean_docs,
        embedding=embedding,
        collection_name="aesthetic_collection",
        persist_directory="fresh_db",  
        client_settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

    # Step 3: Define chat prompt with context and memory placeholder
    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You are an AI assistant at an aesthetics clinic.\n"
        "Use ONLY the facts in Context.\n"
        "If the exact price is not present, say you don't know and suggest booking a consultation.\n"
        "NEVER invent ranges or placeholders like XX. Keep currency symbols as-is.\n\n"
        "Context:\n{context}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ])

    # Step 4: Define how to pass full inputs to the prompt
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def build_inputs(inputs):
        return {
            "context": format_docs(retriever.invoke(inputs["question"])),
            "question": inputs["question"],
            "history": inputs.get("history", [])
        }

    # Step 5: Create the base chain
    chain = (
        RunnableLambda(build_inputs)
        | prompt
        | ChatOpenAI(temperature=0)
        | StrOutputParser()
    )

    # Step 6: Add per-session chat history memory
    final_chain = RunnableWithMessageHistory(
        chain,
        lambda session_id: chat_histories.setdefault(session_id, InMemoryChatMessageHistory()),
        input_messages_key="question",
        history_messages_key="history",
    )

    return final_chain



