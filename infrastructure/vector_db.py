"""
Vector Database Integration cho hệ thống AIOps Đa Tác Nhân

Module này cung cấp tích hợp với:
- Milvus: Open-source vector database
- Pinecone: Managed vector database service
- Semantic search cho log analysis và knowledge retrieval
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
import json
import os

# LangChain embeddings
try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_anthropic import AnthropicEmbeddings
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("LangChain embeddings không được cài đặt. Một số tính năng sẽ bị giới hạn.")

# Milvus imports
try:
    from pymilvus import (
        connections,
        utility,
        FieldSchema,
        CollectionSchema,
        DataType,
        Collection,
        AnnSearchParam,
        SearchResult
    )
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    logging.warning("Milvus không được cài đặt. Một số tính năng sẽ bị giới hạn.")

# Pinecone imports
try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logging.warning("Pinecone không được cài đặt. Một số tính năng sẽ bị giới hạn.")

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class VectorDocument:
    """Một document với vector embedding"""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SearchResult:
    """Kết quả tìm kiếm vector"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Milvus Vector Database
# ============================================================================

class MilvusVectorDB:
    """Vector database với Milvus"""
    
    def __init__(self, host: str = "localhost", port: int = 19530,
                 alias: str = "default"):
        """
        Khởi tạo Milvus Vector DB
        
        Args:
            host (str): Milvus host
            port (int): Milvus port
            alias (str): Connection alias
        """
        if not MILVUS_AVAILABLE:
            raise ImportError("Milvus không được cài đặt")
        
        self.host = host
        self.port = port
        self.alias = alias
        
        # Connect to Milvus
        connections.connect(alias=alias, host=host, port=port)
        
        logger.info(f"Đã kết nối tới Milvus tại {host}:{port}")
    
    def create_collection(self, collection_name: str, dimension: int = 1536,
                         description: str = "") -> bool:
        """
        Tạo collection
        
        Args:
            collection_name (str): Tên collection
            dimension (int): Dimension của vector
            description (str): Mô tả collection
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra collection đã tồn tại chưa
            if utility.has_collection(collection_name):
                logger.info(f"Collection {collection_name} đã tồn tại")
                return True
            
            # Định nghĩa schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=100)
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description=description
            )
            
            # Tạo collection
            collection = Collection(
                name=collection_name,
                schema=schema
            )
            
            # Tạo index
            index_params = {
                "metric_type": "IP",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            
            logger.info(f"Đã tạo collection {collection_name} thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo collection {collection_name}: {str(e)}")
            return False
    
    def insert_embeddings(self, collection_name: str, documents: List[VectorDocument]) -> int:
        """
        Insert embeddings vào collection
        
        Args:
            collection_name (str): Tên collection
            documents (List[VectorDocument]): Danh sách documents
            
        Returns:
            int: Số lượng documents đã insert
        """
        try:
            collection = Collection(collection_name)
            
            # Chuẩn bị data
            ids = [doc.id for doc in documents]
            texts = [doc.text for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            timestamps = [doc.timestamp for doc in documents]
            
            # Insert
            data = [ids, texts, embeddings, metadatas, timestamps]
            insert_result = collection.insert(data)
            
            # Flush để đảm bảo data được persist
            collection.flush()
            
            logger.info(f"Đã insert {len(documents)} documents vào {collection_name}")
            return len(documents)
            
        except Exception as e:
            logger.error(f"Lỗi khi insert embeddings: {str(e)}")
            return 0
    
    def search_similar(self, collection_name: str, query_embedding: List[float],
                      top_k: int = 10) -> List[SearchResult]:
        """
        Tìm kiếm similar vectors
        
        Args:
            collection_name (str): Tên collection
            query_embedding (List[float]): Query embedding
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[SearchResult]: Danh sách kết quả tìm kiếm
        """
        try:
            collection = Collection(collection_name)
            collection.load()
            
            # Tìm kiếm
            search_params = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }
            
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=None,
                output_fields=["id", "text", "metadata", "timestamp"]
            )
            
            # Parse kết quả
            search_results = []
            for result in results[0]:
                search_results.append(SearchResult(
                    id=result.entity.get("id"),
                    text=result.entity.get("text"),
                    score=result.score,
                    metadata=result.entity.get("metadata", {})
                ))
            
            logger.info(f"Đã tìm thấy {len(search_results)} kết quả")
            return search_results
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm similar vectors: {str(e)}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Xóa collection
        
        Args:
            collection_name (str): Tên collection
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Drop collection
            utility.drop_collection(collection_name)
            
            logger.info(f"Đã xóa collection {collection_name} thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi xóa collection {collection_name}: {str(e)}")
            return False


# ============================================================================
# Pinecone Vector Database
# ============================================================================

class PineconeVectorDB:
    """Vector database với Pinecone"""
    
    def __init__(self, api_key: str, environment: str = "us-west1-gcp"):
        """
        Khởi tạo Pinecone Vector DB
        
        Args:
            api_key (str): Pinecone API key
            environment (str): Pinecone environment
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone không được cài đặt")
        
        self.api_key = api_key
        self.environment = environment
        
        # Initialize Pinecone
        pinecone.init(api_key=api_key, environment=environment)
        
        logger.info(f"Đã kết nối tới Pinecone environment: {environment}")
    
    def create_index(self, index_name: str, dimension: int = 1536,
                    metric: str = "cosine") -> bool:
        """
        Tạo index
        
        Args:
            index_name (str): Tên index
            dimension (int): Dimension của vector
            metric (str): Metric (cosine, euclidean, dotproduct)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra index đã tồn tại chưa
            if index_name in pinecone.list_indexes():
                logger.info(f"Index {index_name} đã tồn tại")
                return True
            
            # Tạo index
            pinecone.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric
            )
            
            logger.info(f"Đã tạo index {index_name} thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo index {index_name}: {str(e)}")
            return False
    
    def upsert_vectors(self, index_name: str, documents: List[VectorDocument]) -> int:
        """
        Upsert vectors vào index
        
        Args:
            index_name (str): Tên index
            documents (List[VectorDocument]): Danh sách documents
            
        Returns:
            int: Số lượng documents đã upsert
        """
        try:
            index = pinecone.Index(index_name)
            
            # Chuẩn bị vectors
            vectors = []
            for doc in documents:
                vectors.append({
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {
                        "text": doc.text,
                        **doc.metadata,
                        "timestamp": doc.timestamp
                    }
                })
            
            # Upsert
            index.upsert(vectors=vectors)
            
            logger.info(f"Đã upsert {len(documents)} documents vào {index_name}")
            return len(documents)
            
        except Exception as e:
            logger.error(f"Lỗi khi upsert vectors: {str(e)}")
            return 0
    
    def query_vectors(self, index_name: str, query_embedding: List[float],
                     top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Query vectors
        
        Args:
            index_name (str): Tên index
            query_embedding (List[float]): Query embedding
            top_k (int): Số lượng kết quả trả về
            filter (Optional[Dict[str, Any]]): Filter conditions
            
        Returns:
            List[SearchResult]: Danh sách kết quả tìm kiếm
        """
        try:
            index = pinecone.Index(index_name)
            
            # Query
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )
            
            # Parse kết quả
            search_results = []
            for match in results["matches"]:
                metadata = match.get("metadata", {})
                search_results.append(SearchResult(
                    id=match["id"],
                    text=metadata.get("text", ""),
                    score=match["score"],
                    metadata={k: v for k, v in metadata.items() if k != "text"}
                ))
            
            logger.info(f"Đã tìm thấy {len(search_results)} kết quả")
            return search_results
            
        except Exception as e:
            logger.error(f"Lỗi khi query vectors: {str(e)}")
            return []
    
    def delete_index(self, index_name: str) -> bool:
        """
        Xóa index
        
        Args:
            index_name (str): Tên index
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            pinecone.delete_index(index_name)
            
            logger.info(f"Đã xóa index {index_name} thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi xóa index {index_name}: {str(e)}")
            return False


# ============================================================================
# Embedding Generator
# ============================================================================

class EmbeddingGenerator:
    """Generator cho embeddings"""
    
    def __init__(self, model_name: str = "text-embedding-ada-002",
                 provider: str = "openai", api_key: Optional[str] = None):
        """
        Khởi tạo Embedding Generator
        
        Args:
            model_name (str): Tên model embedding
            provider (str): Provider (openai, anthropic, google)
            api_key (Optional[str]): API key
        """
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError("LangChain embeddings không được cài đặt")
        
        self.model_name = model_name
        self.provider = provider
        
        # Khởi tạo embedding model
        if provider == "openai":
            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                openai_api_key=api_key or os.getenv("OPENAI_API_KEY")
            )
        elif provider == "anthropic":
            self.embeddings = AnthropicEmbeddings(
                model=model_name,
                anthropic_api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
            )
        elif provider == "google":
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=api_key or os.getenv("GOOGLE_API_KEY")
            )
        else:
            raise ValueError(f"Provider không được hỗ trợ: {provider}")
        
        logger.info(f"Đã khởi tạo Embedding Generator với {provider} - {model_name}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings cho danh sách texts
        
        Args:
            texts (List[str]): Danh sách texts
            
        Returns:
            List[List[float]]: Danh sách embeddings
        """
        try:
            logger.info(f"Đang generate embeddings cho {len(texts)} texts...")
            
            embeddings = self.embeddings.embed_documents(texts)
            
            logger.info(f"Đã generate {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Lỗi khi generate embeddings: {str(e)}")
            return []
    
    def batch_generate(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Batch generate embeddings
        
        Args:
            texts (List[str]): Danh sách texts
            batch_size (int): Kích thước batch
            
        Returns:
            List[List[float]]: Danh sách embeddings
        """
        try:
            logger.info(f"Đang batch generate embeddings cho {len(texts)} texts...")
            
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                embeddings = self.generate_embeddings(batch)
                all_embeddings.extend(embeddings)
            
            logger.info(f"Đã batch generate {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Lỗi khi batch generate embeddings: {str(e)}")
            return []
    
    def get_embedding_model(self):
        """
        Lấy embedding model
        
        Returns:
            Embedding model object
        """
        return self.embeddings


# ============================================================================
# Semantic Search Engine
# ============================================================================

class SemanticSearchEngine:
    """Semantic search engine"""
    
    def __init__(self, vector_db: Union[MilvusVectorDB, PineconeVectorDB],
                 embedding_generator: EmbeddingGenerator):
        """
        Khởi tạo Semantic Search Engine
        
        Args:
            vector_db (Union[MilvusVectorDB, PineconeVectorDB]): Vector database
            embedding_generator (EmbeddingGenerator): Embedding generator
        """
        self.vector_db = vector_db
        self.embedding_generator = embedding_generator
        logger.info("Semantic Search Engine đã được khởi tạo thành công")
    
    def search_knowledge_base(self, query: str, collection_name: str,
                             top_k: int = 10) -> List[SearchResult]:
        """
        Tìm kiếm trong knowledge base
        
        Args:
            query (str): Query
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[SearchResult]: Danh sách kết quả tìm kiếm
        """
        try:
            logger.info(f"Đang tìm kiếm knowledge base: {query}")
            
            # Generate embedding cho query
            query_embedding = self.embedding_generator.generate_embeddings([query])[0]
            
            # Tìm kiếm
            if isinstance(self.vector_db, MilvusVectorDB):
                results = self.vector_db.search_similar(collection_name, query_embedding, top_k)
            else:
                results = self.vector_db.query_vectors(collection_name, query_embedding, top_k)
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm knowledge base: {str(e)}")
            return []
    
    def search_similar_incidents(self, incident_logs: str, collection_name: str,
                                 top_k: int = 10) -> List[SearchResult]:
        """
        Tìm kiếm incidents tương tự
        
        Args:
            incident_logs (str): Log sự cố
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[SearchResult]: Danh sách kết quả tìm kiếm
        """
        try:
            logger.info("Đang tìm kiếm incidents tương tự...")
            
            # Generate embedding cho incident logs
            incident_embedding = self.embedding_generator.generate_embeddings([incident_logs])[0]
            
            # Tìm kiếm
            if isinstance(self.vector_db, MilvusVectorDB):
                results = self.vector_db.search_similar(collection_name, incident_embedding, top_k)
            else:
                results = self.vector_db.query_vectors(collection_name, incident_embedding, top_k)
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm incidents tương tự: {str(e)}")
            return []
    
    def search_runbooks(self, query: str, collection_name: str,
                       top_k: int = 10) -> List[SearchResult]:
        """
        Tìm kiếm runbooks
        
        Args:
            query (str): Query
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[SearchResult]: Danh sách kết quả tìm kiếm
        """
        try:
            logger.info(f"Đang tìm kiếm runbooks: {query}")
            
            # Generate embedding cho query
            query_embedding = self.embedding_generator.generate_embeddings([query])[0]
            
            # Tìm kiếm
            if isinstance(self.vector_db, MilvusVectorDB):
                results = self.vector_db.search_similar(collection_name, query_embedding, top_k)
            else:
                results = self.vector_db.query_vectors(collection_name, query_embedding, top_k)
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm runbooks: {str(e)}")
            return []
    
    def hybrid_search(self, query: str, collection_name: str,
                     keyword_filter: Optional[Dict[str, Any]] = None,
                     top_k: int = 10) -> List[SearchResult]:
        """
        Hybrid search (semantic + keyword)
        
        Args:
            query (str): Query
            collection_name (str): Tên collection/index
            keyword_filter (Optional[Dict[str, Any]]): Filter conditions
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[SearchResult]: Danh sách kết quả tìm kiếm
        """
        try:
            logger.info(f"Đang thực hiện hybrid search: {query}")
            
            # Generate embedding cho query
            query_embedding = self.embedding_generator.generate_embeddings([query])[0]
            
            # Tìm kiếm với filter
            if isinstance(self.vector_db, MilvusVectorDB):
                # Milvus không hỗ trợ filter trực tiếp trong search_similar
                # Cần implement custom logic
                results = self.vector_db.search_similar(collection_name, query_embedding, top_k)
            else:
                # Pinecone hỗ trợ filter
                results = self.vector_db.query_vectors(
                    collection_name,
                    query_embedding,
                    top_k,
                    filter=keyword_filter
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện hybrid search: {str(e)}")
            return []


# ============================================================================
# Knowledge Retriever
# ============================================================================

class KnowledgeRetriever:
    """Retriever cho knowledge"""
    
    def __init__(self, semantic_search_engine: SemanticSearchEngine):
        """
        Khởi tạo Knowledge Retriever
        
        Args:
            semantic_search_engine (SemanticSearchEngine): Semantic search engine
        """
        self.search_engine = semantic_search_engine
        logger.info("Knowledge Retriever đã được khởi tạo thành công")
    
    def retrieve_context(self, query: str, collection_name: str,
                        top_k: int = 5) -> List[str]:
        """
        Retrieve context cho query
        
        Args:
            query (str): Query
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[str]: Danh sách context
        """
        try:
            results = self.search_engine.search_knowledge_base(query, collection_name, top_k)
            return [result.text for result in results]
        except Exception as e:
            logger.error(f"Lỗi khi retrieve context: {str(e)}")
            return []
    
    def retrieve_relevant_logs(self, incident_logs: str, collection_name: str,
                              top_k: int = 5) -> List[str]:
        """
        Retrieve relevant logs
        
        Args:
            incident_logs (str): Log sự cố
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[str]: Danh sách relevant logs
        """
        try:
            results = self.search_engine.search_similar_incidents(incident_logs, collection_name, top_k)
            return [result.text for result in results]
        except Exception as e:
            logger.error(f"Lỗi khi retrieve relevant logs: {str(e)}")
            return []
    
    def retrieve_solutions(self, query: str, collection_name: str,
                          top_k: int = 5) -> List[str]:
        """
        Retrieve solutions
        
        Args:
            query (str): Query
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[str]: Danh sách solutions
        """
        try:
            results = self.search_engine.search_runbooks(query, collection_name, top_k)
            return [result.text for result in results]
        except Exception as e:
            logger.error(f"Lỗi khi retrieve solutions: {str(e)}")
            return []
    
    def rank_results(self, results: List[SearchResult],
                    relevance_weights: Optional[Dict[str, float]] = None) -> List[SearchResult]:
        """
        Rank kết quả tìm kiếm
        
        Args:
            results (List[SearchResult]): Danh sách kết quả
            relevance_weights (Optional[Dict[str, float]]): Weights cho ranking
            
        Returns:
            List[SearchResult]: Danh sách kết quả đã rank
        """
        try:
            if not relevance_weights:
                relevance_weights = {
                    "score": 0.7,
                    "recency": 0.3
                }
            
            # Tính toán composite score
            for result in results:
                composite_score = (
                    result.score * relevance_weights.get("score", 0.7)
                )
                
                # Thêm recency score nếu có timestamp
                if "timestamp" in result.metadata:
                    try:
                        timestamp = datetime.fromisoformat(result.metadata["timestamp"])
                        days_old = (datetime.now() - timestamp).days
                        recency_score = max(0, 1 - days_old / 365)  # Decay trong 1 năm
                        composite_score += recency_score * relevance_weights.get("recency", 0.3)
                    except:
                        pass
                
                result.score = composite_score
            
            # Sort by score
            ranked_results = sorted(results, key=lambda x: x.score, reverse=True)
            
            return ranked_results
            
        except Exception as e:
            logger.error(f"Lỗi khi rank results: {str(e)}")
            return results


# ============================================================================
# Main Vector DB Manager
# ============================================================================

class VectorDBManager:
    """Main orchestrator cho Vector Database"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Khởi tạo Vector DB Manager
        
        Args:
            config (Dict[str, Any]): Cấu hình
        """
        self.config = config
        self.vector_db = None
        self.embedding_generator = None
        self.semantic_search_engine = None
        self.knowledge_retriever = None
        
        logger.info("Vector DB Manager đã được khởi tạo thành công")
    
    def setup_vector_db(self) -> bool:
        """
        Setup vector database
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Đang setup vector database...")
            
            # Khởi tạo vector database
            db_type = self.config.get("type", "milvus")
            
            if db_type == "milvus":
                self.vector_db = MilvusVectorDB(
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 19530)
                )
            elif db_type == "pinecone":
                self.vector_db = PineconeVectorDB(
                    api_key=self.config.get("api_key"),
                    environment=self.config.get("environment", "us-west1-gcp")
                )
            else:
                raise ValueError(f"Vector database type không được hỗ trợ: {db_type}")
            
            # Khởi tạo embedding generator
            self.embedding_generator = EmbeddingGenerator(
                model_name=self.config.get("embedding_model", "text-embedding-ada-002"),
                provider=self.config.get("embedding_provider", "openai"),
                api_key=self.config.get("embedding_api_key")
            )
            
            # Khởi tạo semantic search engine
            self.semantic_search_engine = SemanticSearchEngine(
                self.vector_db,
                self.embedding_generator
            )
            
            # Khởi tạo knowledge retriever
            self.knowledge_retriever = KnowledgeRetriever(self.semantic_search_engine)
            
            # Tạo collections/indexes
            collections = self.config.get("collections", [])
            for collection_config in collections:
                collection_name = collection_config["name"]
                dimension = collection_config.get("dimension", 1536)
                
                if isinstance(self.vector_db, MilvusVectorDB):
                    self.vector_db.create_collection(collection_name, dimension)
                else:
                    self.vector_db.create_index(collection_name, dimension)
            
            logger.info("Đã setup vector database thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi setup vector database: {str(e)}")
            return False
    
    def index_knowledge(self, collection_name: str, documents: List[Dict[str, Any]]) -> int:
        """
        Index knowledge vào vector database
        
        Args:
            collection_name (str): Tên collection/index
            documents (List[Dict[str, Any]]): Danh sách documents
            
        Returns:
            int: Số lượng documents đã index
        """
        try:
            logger.info(f"Đang index {len(documents)} documents vào {collection_name}...")
            
            # Generate embeddings
            texts = [doc["text"] for doc in documents]
            embeddings = self.embedding_generator.generate_embeddings(texts)
            
            # Tạo vector documents
            vector_docs = []
            for i, doc in enumerate(documents):
                vector_doc = VectorDocument(
                    id=doc.get("id", f"doc_{i}"),
                    text=doc["text"],
                    embedding=embeddings[i],
                    metadata=doc.get("metadata", {}),
                    timestamp=doc.get("timestamp", datetime.now().isoformat())
                )
                vector_docs.append(vector_doc)
            
            # Insert vào vector database
            if isinstance(self.vector_db, MilvusVectorDB):
                count = self.vector_db.insert_embeddings(collection_name, vector_docs)
            else:
                count = self.vector_db.upsert_vectors(collection_name, vector_docs)
            
            logger.info(f"Đã index {count} documents")
            return count
            
        except Exception as e:
            logger.error(f"Lỗi khi index knowledge: {str(e)}")
            return 0
    
    def search_and_retrieve(self, query: str, collection_name: str,
                           top_k: int = 10) -> List[SearchResult]:
        """
        Search và retrieve knowledge
        
        Args:
            query (str): Query
            collection_name (str): Tên collection/index
            top_k (int): Số lượng kết quả trả về
            
        Returns:
            List[SearchResult]: Danh sách kết quả
        """
        try:
            results = self.semantic_search_engine.search_knowledge_base(
                query,
                collection_name,
                top_k
            )
            
            # Rank kết quả
            ranked_results = self.knowledge_retriever.rank_results(results)
            
            return ranked_results
            
        except Exception as e:
            logger.error(f"Lỗi khi search và retrieve: {str(e)}")
            return []
    
    def manage_collections(self) -> Dict[str, Any]:
        """
        Quản lý collections/indexes
        
        Returns:
            Dict[str, Any]: Thông tin về collections
        """
        try:
            info = {
                "type": "milvus" if isinstance(self.vector_db, MilvusVectorDB) else "pinecone",
                "collections": []
            }
            
            if isinstance(self.vector_db, MilvusVectorDB):
                # Lấy danh sách collections từ Milvus
                from pymilvus import utility
                collections = utility.list_collections()
                info["collections"] = collections
            else:
                # Lấy danh sách indexes từ Pinecone
                indexes = pinecone.list_indexes()
                info["collections"] = indexes
            
            return info
            
        except Exception as e:
            logger.error(f"Lỗi khi quản lý collections: {str(e)}")
            return {}