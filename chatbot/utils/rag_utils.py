"""
Retrieval-Augmented Generation (RAG) Utilities for document processing,
embedding storage, and conversational retrieval chains using Google Generative AI.

This module provides utilities for:
1. Interacting with Google Generative AI models for content generation.
2. Processing and splitting PDF documents into chunks for embedding.
3. Managing embeddings and vector stores using FAISS.
4. Creating conversational retrieval chains for Q&A with document context.
5. Querying multiple vector stores and combining responses intelligently.
6. Cleaning up vector stores, metadata, and associated documents.
"""
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential

from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

from chatbot.utils.ask_gemini import ask_gemini

@dataclass
class DocumentMetadata:
    """
    Metadata for processed documents.
    """
    doc_id: str
    chunk_size: int
    chunk_overlap: int
    num_chunks: int
    embedding_model: str


class RAGProcessor:
    """
    Retrieval-Augmented Generation Processor for managing document embeddings
    and conversational retrieval chains.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        self.vector_store_dir = Path(settings.MEDIA_ROOT) / 'vector_stores'
        self.metadata_dir = Path(settings.MEDIA_ROOT) / 'metadata'
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_store_paths(self, doc_id: str) -> Tuple[Path, Path]:
        """
        Get paths for vector store and metadata files.

        Args:
            doc_id (str): Unique document identifier.

        Returns:
            Tuple[Path, Path]: Paths for the vector store and metadata file.
        """
        vector_store = self.vector_store_dir / f'store_{doc_id}'
        metadata_file = self.metadata_dir / f'meta_{doc_id}.json'
        return vector_store, metadata_file

    def process_document(self, file_path: str, doc_id: str) -> str:
        """
        Process a PDF document, create embeddings, and store them in a vector store.

        Args:
            file_path (str): Path to the PDF file.
            doc_id (str): Unique document identifier.

        Returns:
            str: Path to the stored vector store.

        Raises:
            ValueError: If any error occurs during document processing.
        """
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            chunk_size = 1000
            chunk_overlap = 200
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
            chunks = text_splitter.split_documents(documents)

            vector_store = FAISS.from_documents(chunks, self.embeddings)
            vector_store_path, metadata_path = self.get_store_paths(doc_id)
            vector_store.save_local(str(vector_store_path))

            metadata = DocumentMetadata(
                doc_id=doc_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                num_chunks=len(chunks),
                embedding_model="models/embedding-001"
            )
            with open(metadata_path, 'w', encoding="utf-8") as f:
                json.dump(asdict(metadata), f)

            return str(vector_store_path)

        except Exception as e:
            raise ValueError(f"Error processing document: {str(e)}") from e

    def get_retrieval_chain(self, vector_store_path: str) -> ConversationalRetrievalChain:
        """
        Create a conversational retrieval chain.

        Args:
            vector_store_path (str): Path to the vector store.

        Returns:
            ConversationalRetrievalChain: Configured conversational retrieval chain.

        Raises:
            ValueError: If the retrieval chain cannot be created.
        """
        try:
            vector_store = FAISS.load_local(
                vector_store_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )

            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-002",
                google_api_key=self.api_key,
                temperature=0.7,
                top_k=3,
                top_p=0.8,
                max_output_tokens=1024
            )

            prompt_template = """Answer the question based on the provided context.
            If the answer cannot be found in the context, acknowledge that and provide a general response.

            Context: {context}
            Chat History: {chat_history}
            Current Question: {question}
            """
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "chat_history", "question"]
            )
            chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=vector_store.as_retriever(
                    search_kwargs={
                        "k": 2,
                        "fetch_k": 5,
                        "search_type": "mmr",
                        "lambda_mult": 0.7 
                    }
                ),
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": prompt},
                verbose=True
            )
            return chain

        except Exception as e:
            raise Exception(f"Error creating retrieval chain: {str(e)}") from e

    @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=lambda retry_state: isinstance(retry_state.outcome.exception(),
                                         exceptions.ResourceExhausted)
    )
    def query_documents(
        self,
        vector_store_paths: List[str],
        query: str,
        chat_history: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """Query multiple documents using the retrieval chain after checking relevance threshold."""
        try:
            if not vector_store_paths:
                return None

            formatted_history = [
                (msg["message"], msg["response"])
                for msg in chat_history
                if msg.get("message") and msg.get("response")
            ]

            all_responses = []
            document_relevance_threshold = 0.7

            for store_path in vector_store_paths:
                if not os.path.exists(store_path):
                    continue

                vector_store = FAISS.load_local(
                    store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )

                similarity_results = vector_store.similarity_search_with_score(query)
                # print(f'similarity result is:{similarity_results}')

                if similarity_results and similarity_results[0][1] > document_relevance_threshold:
                    continue

                chain=self.get_retrieval_chain(store_path)
                result = chain({
                    "question": query,
                    "chat_history": formatted_history or []
                })
                if result.get("answer"):
                    all_responses.append(result["answer"])

            if not all_responses:
                all_responses.append(ask_gemini(query, formatted_history))
            return " ".join(all_responses)

        except exceptions.ResourceExhausted:
            print("Google API quota exceeded. Waiting before retry.")
            time.sleep(30)
            raise
        except Exception as e:
            print(f"Query error: {e}")
            return None

    def cleanup_vector_stores(self) -> None:
        """Clean up vector stores, metadata, and associated PDFs immediately when called."""        
        for store_path in self.vector_store_dir.glob('store_*'):
            try:
                if store_path.is_dir():
                    shutil.rmtree(store_path)
                    print(f"Deleted store: {store_path}")

                meta_path = self.metadata_dir / f'meta_{store_path.name[6:]}.json'
                if meta_path.exists():
                    meta_path.unlink()
                    print(f"Deleted metadata: {meta_path}")

            except Exception as e:
                print(f"Error cleaning up {store_path}: {e}")

        documents_dir = Path("media/documents")
        for pdf_path in documents_dir.glob("*.pdf"):
            try:
                pdf_path.unlink()
            except Exception as e:
                print(f"Error cleaning up PDF {pdf_path}: {e}")
