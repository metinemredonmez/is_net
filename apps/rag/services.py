"""
IOSP - RAG Pipeline Services
Doküman işleme, embedding ve retrieval
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from django.conf import settings

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Qdrant
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

# Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """RAG configuration"""
    ollama_base_url: str = settings.OLLAMA_BASE_URL
    ollama_model: str = settings.OLLAMA_MODEL
    embedding_model: str = settings.OLLAMA_EMBEDDING_MODEL
    qdrant_host: str = settings.QDRANT_HOST
    qdrant_port: int = settings.QDRANT_PORT
    collection_name: str = settings.QDRANT_COLLECTION
    chunk_size: int = settings.CHUNK_SIZE
    chunk_overlap: int = settings.CHUNK_OVERLAP


class DocumentProcessor:
    """Doküman yükleme ve chunk'lama"""

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Dokümanı yükle ve parse et"""
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.pdf':
                loader = PyPDFLoader(file_path)
            elif ext in ['.docx', '.doc']:
                loader = Docx2txtLoader(file_path)
            elif ext in ['.txt', '.md']:
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                raise ValueError(f"Desteklenmeyen dosya türü: {ext}")

            documents = loader.load()
            logger.info(f"Doküman yüklendi: {file_path}, {len(documents)} sayfa")
            return documents

        except Exception as e:
            logger.error(f"Doküman yükleme hatası: {e}")
            raise

    def split_document(self, documents: List) -> List[Dict[str, Any]]:
        """Dokümanı chunk'lara böl"""
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Doküman {len(chunks)} chunk'a bölündü")
        return chunks


class EmbeddingService:
    """Embedding oluşturma servisi"""

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.embeddings = OllamaEmbeddings(
            base_url=self.config.ollama_base_url,
            model=self.config.embedding_model
        )

    def embed_text(self, text: str) -> List[float]:
        """Tek metin için embedding"""
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Çoklu metin için embedding"""
        return self.embeddings.embed_documents(texts)


class VectorStoreService:
    """Qdrant vector store yönetimi"""

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.client = QdrantClient(
            host=self.config.qdrant_host,
            port=self.config.qdrant_port
        )
        self.embedding_service = EmbeddingService(config)
        self._ensure_collection()

    def _ensure_collection(self):
        """Collection yoksa oluştur"""
        collections = self.client.get_collections().collections
        if not any(c.name == self.config.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=4096,  # nomic-embed-text dimension
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Qdrant collection oluşturuldu: {self.config.collection_name}")

    def get_vectorstore(self) -> Qdrant:
        """LangChain Qdrant wrapper"""
        return Qdrant(
            client=self.client,
            collection_name=self.config.collection_name,
            embeddings=self.embedding_service.embeddings
        )

    def add_documents(self, documents: List, metadata: Dict = None) -> List[str]:
        """Dokümanları vector store'a ekle"""
        vectorstore = self.get_vectorstore()
        ids = vectorstore.add_documents(documents)
        logger.info(f"{len(ids)} chunk vector store'a eklendi")
        return ids

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Semantic search"""
        vectorstore = self.get_vectorstore()
        results = vectorstore.similarity_search_with_score(query, k=k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]


class RAGService:
    """Ana RAG servisi - query processing"""

    SYSTEM_PROMPT = """Sen İşNet'in kurumsal bilgi asistanısın.
Sana verilen bağlam bilgilerini kullanarak soruları yanıtla.

Kurallar:
1. Sadece verilen bağlamdan cevap ver
2. Emin olmadığın bilgileri uydurmak
3. Cevabın kaynağını belirt
4. Türkçe yanıt ver
5. Profesyonel ve net ol

Bağlam:
{context}

Soru: {question}

Cevap:"""

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.vector_store = VectorStoreService(config)
        self.llm = Ollama(
            base_url=self.config.ollama_base_url,
            model=self.config.ollama_model,
            temperature=0.1
        )
        self.prompt = PromptTemplate(
            template=self.SYSTEM_PROMPT,
            input_variables=["context", "question"]
        )

    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """
        RAG query - soru sor ve cevap al

        Returns:
            {
                "answer": str,
                "sources": List[Dict],
                "confidence": float
            }
        """
        # 1. Retrieve relevant documents
        search_results = self.vector_store.search(question, k=k)

        if not search_results:
            return {
                "answer": "Bu soruyla ilgili doküman bulunamadı.",
                "sources": [],
                "confidence": 0.0
            }

        # 2. Build context
        context = "\n\n---\n\n".join([
            f"[Kaynak {i+1}]: {r['content']}"
            for i, r in enumerate(search_results)
        ])

        # 3. Generate answer
        prompt_text = self.prompt.format(context=context, question=question)
        answer = self.llm.invoke(prompt_text)

        # 4. Calculate confidence (average similarity score)
        avg_score = sum(r['score'] for r in search_results) / len(search_results)
        confidence = max(0, min(1, 1 - avg_score))  # Convert distance to similarity

        return {
            "answer": answer,
            "sources": [
                {
                    "content": r['content'][:200] + "...",
                    "metadata": r['metadata'],
                    "relevance": 1 - r['score']
                }
                for r in search_results[:3]  # Top 3 sources
            ],
            "confidence": round(confidence, 2)
        }

    def process_document(self, document_id: str) -> Dict[str, Any]:
        """
        Dokümanı işle ve vector store'a ekle

        Args:
            document_id: Django Document model ID

        Returns:
            {"success": bool, "chunk_count": int, "error": str}
        """
        from apps.documents.models import Document, DocumentChunk
        from django.utils import timezone

        try:
            doc = Document.objects.get(id=document_id)
            doc.status = 'processing'
            doc.save()

            # 1. Load document
            processor = DocumentProcessor(self.config)
            documents = processor.load_document(doc.file.path)

            # 2. Split into chunks
            chunks = processor.split_document(documents)

            # 3. Add to vector store
            vector_ids = self.vector_store.add_documents(chunks)

            # 4. Save chunks to database
            for i, (chunk, vid) in enumerate(zip(chunks, vector_ids)):
                DocumentChunk.objects.create(
                    document=doc,
                    chunk_index=i,
                    content=chunk.page_content,
                    token_count=len(chunk.page_content.split()),
                    vector_id=vid,
                    page_number=chunk.metadata.get('page', None),
                    metadata=chunk.metadata
                )

            # 5. Update document status
            doc.status = 'completed'
            doc.chunk_count = len(chunks)
            doc.processed_at = timezone.now()
            doc.save()

            logger.info(f"Doküman işlendi: {doc.title}, {len(chunks)} chunk")
            return {"success": True, "chunk_count": len(chunks)}

        except Exception as e:
            logger.error(f"Doküman işleme hatası: {e}")
            if 'doc' in locals():
                doc.status = 'failed'
                doc.error_message = str(e)
                doc.save()
            return {"success": False, "error": str(e)}


# Singleton instance
_rag_service = None


def get_rag_service() -> RAGService:
    """RAG service singleton"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
