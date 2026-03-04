"""
ELK Stack Integration cho hệ thống AIOps Đa Tác Nhân

Module này cung cấp tích hợp với:
- Elasticsearch: Centralized logging và log storage
- Logstash: Log ingestion và processing pipeline
- Kibana: Visualization và dashboard
- ELSER: Semantic search cho log analysis
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
import json
import os

# Elasticsearch imports
try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    logging.warning("Elasticsearch không được cài đặt. Một số tính năng sẽ bị giới hạn.")

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class LogEntry:
    """Một entry log"""
    timestamp: str
    level: str
    service: str
    message: str
    incident_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Kết quả tìm kiếm"""
    hits: List[Dict[str, Any]]
    total: int
    took: float
    aggregations: Optional[Dict[str, Any]] = None


# ============================================================================
# Elasticsearch Client
# ============================================================================

class ElasticsearchClient:
    """Client cho Elasticsearch"""
    
    def __init__(self, host: str = "localhost", port: int = 9200,
                 username: Optional[str] = None, password: Optional[str] = None,
                 use_ssl: bool = False):
        """
        Khởi tạo Elasticsearch Client
        
        Args:
            host (str): Elasticsearch host
            port (int): Elasticsearch port
            username (Optional[str]): Username cho authentication
            password (Optional[str]): Password cho authentication
            use_ssl (bool): Có sử dụng SSL không
        """
        if not ELASTICSEARCH_AVAILABLE:
            raise ImportError("Elasticsearch không được cài đặt")
        
        # Tạo connection URL
        scheme = "https" if use_ssl else "http"
        url = f"{scheme}://{host}:{port}"
        
        # Tạo client
        if username and password:
            self.client = Elasticsearch(
                url,
                basic_auth=(username, password),
                verify_certs=False,
                ssl_show_warn=False
            )
        else:
            self.client = Elasticsearch(url)
        
        # Kiểm tra connection
        if self.client.ping():
            logger.info(f"Đã kết nối thành công tới Elasticsearch tại {url}")
        else:
            logger.error(f"Không thể kết nối tới Elasticsearch tại {url}")
            raise ConnectionError(f"Không thể kết nối tới Elasticsearch tại {url}")
    
    def create_index(self, index_name: str, mappings: Optional[Dict[str, Any]] = None,
                    settings: Optional[Dict[str, Any]] = None) -> bool:
        """
        Tạo index
        
        Args:
            index_name (str): Tên index
            mappings (Optional[Dict[str, Any]]): Mappings cho index
            settings (Optional[Dict[str, Any]]): Settings cho index
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra index đã tồn tại chưa
            if self.client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} đã tồn tại")
                return True
            
            # Tạo index body
            body = {}
            if settings:
                body["settings"] = settings
            if mappings:
                body["mappings"] = mappings
            
            # Tạo index
            response = self.client.indices.create(index=index_name, body=body)
            
            if response.get("acknowledged", False):
                logger.info(f"Đã tạo index {index_name} thành công")
                return True
            else:
                logger.error(f"Không thể tạo index {index_name}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi tạo index {index_name}: {str(e)}")
            return False
    
    def index_log(self, index_name: str, log_entry: LogEntry) -> bool:
        """
        Index một log entry
        
        Args:
            index_name (str): Tên index
            log_entry (LogEntry): Log entry cần index
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Chuyển đổi log entry sang dict
            doc = {
                "timestamp": log_entry.timestamp,
                "level": log_entry.level,
                "service": log_entry.service,
                "message": log_entry.message,
                "incident_id": log_entry.incident_id,
                "metadata": log_entry.metadata
            }
            
            # Index document
            response = self.client.index(index=index_name, document=doc)
            
            if response.get("result") in ["created", "updated"]:
                return True
            else:
                logger.error(f"Không thể index log entry: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi index log entry: {str(e)}")
            return False
    
    def search_logs(self, index_name: str, query: Dict[str, Any],
                   size: int = 10, from_: int = 0) -> SearchResult:
        """
        Tìm kiếm logs
        
        Args:
            index_name (str): Tên index
            query (Dict[str, Any]): Query DSL
            size (int): Số lượng kết quả trả về
            from_ (int): Offset
            
        Returns:
            SearchResult: Kết quả tìm kiếm
        """
        try:
            # Chạy search
            response = self.client.search(
                index=index_name,
                body=query,
                size=size,
                from_=from_
            )
            
            # Parse kết quả
            hits = [hit["_source"] for hit in response["hits"]["hits"]]
            total = response["hits"]["total"]["value"]
            took = response["took"]
            aggregations = response.get("aggregations")
            
            return SearchResult(
                hits=hits,
                total=total,
                took=took,
                aggregations=aggregations
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm logs: {str(e)}")
            return SearchResult(hits=[], total=0, took=0)
    
    def bulk_index(self, index_name: str, log_entries: List[LogEntry]) -> int:
        """
        Bulk index logs
        
        Args:
            index_name (str): Tên index
            log_entries (List[LogEntry]): Danh sách log entries
            
        Returns:
            int: Số lượng logs đã index thành công
        """
        try:
            # Chuẩn bị bulk actions
            actions = []
            for log_entry in log_entries:
                action = {
                    "_index": index_name,
                    "_source": {
                        "timestamp": log_entry.timestamp,
                        "level": log_entry.level,
                        "service": log_entry.service,
                        "message": log_entry.message,
                        "incident_id": log_entry.incident_id,
                        "metadata": log_entry.metadata
                    }
                }
                actions.append(action)
            
            # Chạy bulk
            success, failed = bulk(self.client, actions)
            
            logger.info(f"Bulk index: {success} thành công, {failed} thất bại")
            return success
            
        except Exception as e:
            logger.error(f"Lỗi khi bulk index: {str(e)}")
            return 0
    
    def delete_index(self, index_name: str) -> bool:
        """
        Xóa index
        
        Args:
            index_name (str): Tên index
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            response = self.client.indices.delete(index=index_name)
            
            if response.get("acknowledged", False):
                logger.info(f"Đã xóa index {index_name} thành công")
                return True
            else:
                logger.error(f"Không thể xóa index {index_name}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi xóa index {index_name}: {str(e)}")
            return False


# ============================================================================
# Log Ingestion Pipeline
# ============================================================================

class LogIngestionPipeline:
    """Pipeline để ingest logs vào Elasticsearch"""
    
    def __init__(self, es_client: ElasticsearchClient):
        """
        Khởi tạo Log Ingestion Pipeline
        
        Args:
            es_client (ElasticsearchClient): Elasticsearch client
        """
        self.es_client = es_client
        logger.info("Log Ingestion Pipeline đã được khởi tạo thành công")
    
    def ingest_incident_logs(self, incident_logs: str, incident_id: str,
                            service: str = "aiops") -> bool:
        """
        Ingest incident logs
        
        Args:
            incident_logs (str): Log sự cố
            incident_id (str): ID của sự cố
            service (str): Tên service
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Đang ingest incident logs cho {incident_id}...")
            
            # Parse logs thành các entries
            log_entries = self._parse_and_normalize(incident_logs, incident_id, service)
            
            # Bulk index
            success_count = self.es_client.bulk_index("incident_logs", log_entries)
            
            logger.info(f"Đã ingest {success_count}/{len(log_entries)} log entries")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Lỗi khi ingest incident logs: {str(e)}")
            return False
    
    def ingest_system_logs(self, log_file: str, service: str) -> bool:
        """
        Ingest system logs từ file
        
        Args:
            log_file (str): Đường dẫn file log
            service (str): Tên service
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Đang ingest system logs từ {log_file}...")
            
            # Đọc file log
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Parse logs
            log_entries = self._parse_and_normalize(log_content, None, service)
            
            # Bulk index
            success_count = self.es_client.bulk_index("system_logs", log_entries)
            
            logger.info(f"Đã ingest {success_count}/{len(log_entries)} log entries")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Lỗi khi ingest system logs: {str(e)}")
            return False
    
    def _parse_and_normalize(self, log_content: str, incident_id: Optional[str],
                            service: str) -> List[LogEntry]:
        """
        Parse và normalize logs
        
        Args:
            log_content (str): Nội dung log
            incident_id (Optional[str]): ID của sự cố
            service (str): Tên service
            
        Returns:
            List[LogEntry]: Danh sách log entries đã normalize
        """
        try:
            log_entries = []
            lines = log_content.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Parse log line (đơn giản hóa)
                log_entry = self._parse_log_line(line, incident_id, service)
                if log_entry:
                    log_entries.append(log_entry)
            
            # Enrich với metadata
            log_entries = self._enrich_with_metadata(log_entries)
            
            return log_entries
            
        except Exception as e:
            logger.error(f"Lỗi khi parse và normalize logs: {str(e)}")
            return []
    
    def _parse_log_line(self, line: str, incident_id: Optional[str],
                       service: str) -> Optional[LogEntry]:
        """
        Parse một dòng log
        
        Args:
            line (str): Dòng log
            incident_id (Optional[str]): ID của sự cố
            service (str): Tên service
            
        Returns:
            Optional[LogEntry]: Log entry đã parse
        """
        try:
            # Đơn giản hóa: giả định format log
            # [TIMESTAMP] [LEVEL] SERVICE: MESSAGE
            
            # Extract timestamp
            timestamp = datetime.now().isoformat()
            
            # Extract level
            level = "INFO"
            if "ERROR" in line.upper():
                level = "ERROR"
            elif "WARNING" in line.upper() or "WARN" in line.upper():
                level = "WARNING"
            elif "DEBUG" in line.upper():
                level = "DEBUG"
            
            # Extract message
            message = line
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                service=service,
                message=message,
                incident_id=incident_id,
                metadata={}
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi parse log line: {str(e)}")
            return None
    
    def _enrich_with_metadata(self, log_entries: List[LogEntry]) -> List[LogEntry]:
        """
        Enrich logs với metadata
        
        Args:
            log_entries (List[LogEntry]): Danh sách log entries
            
        Returns:
            List[LogEntry]: Danh sách log entries đã enrich
        """
        try:
            # Thêm metadata như hostname, environment, etc.
            for log_entry in log_entries:
                log_entry.metadata.update({
                    "hostname": os.getenv("HOSTNAME", "unknown"),
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "ingested_at": datetime.now().isoformat()
                })
            
            return log_entries
            
        except Exception as e:
            logger.error(f"Lỗi khi enrich metadata: {str(e)}")
            return log_entries


# ============================================================================
# ELSER Semantic Search
# ============================================================================

class ELSERSemanticSearch:
    """Semantic search với ELSER (Elastic Learned Sparse Encoder)"""
    
    def __init__(self, es_client: ElasticsearchClient):
        """
        Khởi tạo ELSER Semantic Search
        
        Args:
            es_client (ElasticsearchClient): Elasticsearch client
        """
        self.es_client = es_client
        self.elser_model_id = ".elser_model_2"
        logger.info("ELSER Semantic Search đã được khởi tạo thành công")
    
    def setup_elser_model(self) -> bool:
        """
        Setup ELSER model
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Đang setup ELSER model...")
            
            # Kiểm tra model đã tồn tại chưa
            if self._check_model_exists():
                logger.info("ELSER model đã tồn tại")
                return True
            
            # Download và deploy ELSER model
            # (Cần Elasticsearch license phù hợp)
            logger.warning("ELSER model cần license phù hợp. Vui lòng setup thủ công.")
            return False
            
        except Exception as e:
            logger.error(f"Lỗi khi setup ELSER model: {str(e)}")
            return False
    
    def _check_model_exists(self) -> bool:
        """Kiểm tra xem ELSER model đã tồn tại chưa"""
        try:
            response = self.es_client.client.ml.get_trained_models(model_id=self.elser_model_id)
            return response.get("count", 0) > 0
        except Exception:
            return False
    
    def create_semantic_index(self, index_name: str) -> bool:
        """
        Tạo semantic index với ELSER
        
        Args:
            index_name (str): Tên index
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Đang tạo semantic index {index_name}...")
            
            # Mappings cho semantic search
            mappings = {
                "properties": {
                    "message": {
                        "type": "text",
                        "fields": {
                            "ml": {
                                "type": "sparse_vector",
                                "model_id": self.elser_model_id,
                                "model_version": "latest"
                            }
                        }
                    },
                    "timestamp": {"type": "date"},
                    "level": {"type": "keyword"},
                    "service": {"type": "keyword"},
                    "incident_id": {"type": "keyword"}
                }
            }
            
            # Tạo index
            return self.es_client.create_index(index_name, mappings=mappings)
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo semantic index: {str(e)}")
            return False
    
    def semantic_search(self, index_name: str, query_text: str,
                       size: int = 10) -> SearchResult:
        """
        Semantic search với ELSER
        
        Args:
            index_name (str): Tên index
            query_text (str): Query text
            size (int): Số lượng kết quả
            
        Returns:
            SearchResult: Kết quả tìm kiếm
        """
        try:
            logger.info(f"Đang thực hiện semantic search: {query_text}")
            
            # Query DSL cho semantic search
            query = {
                "query": {
                    "text_expansion": {
                        "message.ml": {
                            "model_id": self.elser_model_id,
                            "model_text": query_text
                        }
                    }
                }
            }
            
            # Chạy search
            return self.es_client.search_logs(index_name, query, size=size)
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện semantic search: {str(e)}")
            return SearchResult(hits=[], total=0, took=0)
    
    def hybrid_search(self, index_name: str, query_text: str,
                     keyword_query: Optional[str] = None,
                     size: int = 10) -> SearchResult:
        """
        Hybrid search (keyword + semantic)
        
        Args:
            index_name (str): Tên index
            query_text (str): Query text cho semantic search
            keyword_query (Optional[str]): Keyword query
            size (int): Số lượng kết quả
            
        Returns:
            SearchResult: Kết quả tìm kiếm
        """
        try:
            logger.info(f"Đang thực hiện hybrid search: {query_text}")
            
            # Query DSL cho hybrid search
            if keyword_query:
                query = {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "text_expansion": {
                                        "message.ml": {
                                            "model_id": self.elser_model_id,
                                            "model_text": query_text
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "message": keyword_query
                                    }
                                }
                            ]
                        }
                    }
                }
            else:
                return self.semantic_search(index_name, query_text, size)
            
            # Chạy search
            return self.es_client.search_logs(index_name, query, size=size)
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện hybrid search: {str(e)}")
            return SearchResult(hits=[], total=0, took=0)


# ============================================================================
# Kibana Dashboard Integration
# ============================================================================

class KibanaDashboardIntegration:
    """Integration với Kibana Dashboard"""
    
    def __init__(self, kibana_url: str = "http://localhost:5601",
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Khởi tạo Kibana Dashboard Integration
        
        Args:
            kibana_url (str): URL của Kibana
            username (Optional[str]): Username
            password (Optional[str]): Password
        """
        self.kibana_url = kibana_url
        self.username = username
        self.password = password
        logger.info("Kibana Dashboard Integration đã được khởi tạo thành công")
    
    def create_dashboard(self, dashboard_config: Dict[str, Any]) -> bool:
        """
        Tạo dashboard
        
        Args:
            dashboard_config (Dict[str, Any]): Cấu hình dashboard
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Đang tạo Kibana dashboard...")
            
            # Lưu dashboard config vào file
            dashboard_dir = "infrastructure/kibana/dashboards"
            os.makedirs(dashboard_dir, exist_ok=True)
            
            dashboard_file = os.path.join(dashboard_dir, f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Đã lưu dashboard config vào {dashboard_file}")
            logger.info("Vui lòng import dashboard này vào Kibana thủ công")
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo dashboard: {str(e)}")
            return False
    
    def create_visualizations(self, viz_configs: List[Dict[str, Any]]) -> bool:
        """
        Tạo visualizations
        
        Args:
            viz_configs (List[Dict[str, Any]]): Danh sách cấu hình visualizations
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Đang tạo {len(viz_configs)} visualizations...")
            
            # Lưu visualization configs vào file
            viz_dir = "infrastructure/kibana/visualizations"
            os.makedirs(viz_dir, exist_ok=True)
            
            for i, viz_config in enumerate(viz_configs):
                viz_file = os.path.join(viz_dir, f"viz_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                
                with open(viz_file, 'w', encoding='utf-8') as f:
                    json.dump(viz_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Đã lưu {len(viz_configs)} visualization configs")
            logger.info("Vui lòng import các visualizations này vào Kibana thủ công")
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo visualizations: {str(e)}")
            return False
    
    def export_dashboard_config(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """
        Export dashboard config
        
        Args:
            dashboard_id (str): ID của dashboard
            
        Returns:
            Optional[Dict[str, Any]]: Cấu hình dashboard
        """
        try:
            logger.info(f"Đang export dashboard config cho {dashboard_id}...")
            
            # Export dashboard config (cần Kibana API)
            logger.warning("Export dashboard config cần Kibana API. Vui lòng export thủ công.")
            
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi export dashboard config: {str(e)}")
            return None
    
    def import_dashboard_config(self, dashboard_config: Dict[str, Any]) -> bool:
        """
        Import dashboard config
        
        Args:
            dashboard_config (Dict[str, Any]): Cấu hình dashboard
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Đang import dashboard config...")
            
            # Import dashboard config (cần Kibana API)
            logger.warning("Import dashboard config cần Kibana API. Vui lòng import thủ công.")
            
            return False
            
        except Exception as e:
            logger.error(f"Lỗi khi import dashboard config: {str(e)}")
            return False


# ============================================================================
# Main Elasticsearch Manager
# ============================================================================

class ElasticsearchManager:
    """Main orchestrator cho Elasticsearch integration"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Khởi tạo Elasticsearch Manager
        
        Args:
            config (Dict[str, Any]): Cấu hình
        """
        self.config = config
        
        # Khởi tạo Elasticsearch client
        self.es_client = ElasticsearchClient(
            host=config.get("host", "localhost"),
            port=config.get("port", 9200),
            username=config.get("username"),
            password=config.get("password"),
            use_ssl=config.get("use_ssl", False)
        )
        
        # Khởi tạo các components
        self.log_pipeline = LogIngestionPipeline(self.es_client)
        self.elser_search = ELSERSemanticSearch(self.es_client)
        self.kibana_integration = KibanaDashboardIntegration(
            kibana_url=config.get("kibana_url", "http://localhost:5601"),
            username=config.get("kibana_username"),
            password=config.get("kibana_password")
        )
        
        logger.info("Elasticsearch Manager đã được khởi tạo thành công")
    
    def setup_elk_stack(self) -> bool:
        """
        Setup toàn bộ ELK stack
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info("Đang setup ELK stack...")
            
            # Tạo các indexes
            indexes = [
                {
                    "name": "incident_logs",
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "level": {"type": "keyword"},
                            "service": {"type": "keyword"},
                            "message": {"type": "text"},
                            "incident_id": {"type": "keyword"},
                            "metadata": {"type": "object"}
                        }
                    }
                },
                {
                    "name": "system_logs",
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "level": {"type": "keyword"},
                            "service": {"type": "keyword"},
                            "message": {"type": "text"},
                            "metadata": {"type": "object"}
                        }
                    }
                }
            ]
            
            for index_config in indexes:
                self.es_client.create_index(
                    index_config["name"],
                    mappings=index_config.get("mappings")
                )
            
            # Setup ELSER (nếu được cấu hình)
            if self.config.get("enable_elser", False):
                self.elser_search.setup_elser_model()
                self.elser_search.create_semantic_index("semantic_logs")
            
            logger.info("Đã setup ELK stack thành công")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi setup ELK stack: {str(e)}")
            return False
    
    def ingest_and_index(self, log_content: str, incident_id: str,
                        service: str = "aiops") -> bool:
        """
        Ingest và index logs
        
        Args:
            log_content (str): Nội dung log
            incident_id (str): ID của sự cố
            service (str): Tên service
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            return self.log_pipeline.ingest_incident_logs(log_content, incident_id, service)
        except Exception as e:
            logger.error(f"Lỗi khi ingest và index logs: {str(e)}")
            return False
    
    def search_and_analyze(self, query: str, index_name: str = "incident_logs",
                          use_semantic: bool = False) -> SearchResult:
        """
        Tìm kiếm và phân tích logs
        
        Args:
            query (str): Query
            index_name (str): Tên index
            use_semantic (bool): Có sử dụng semantic search không
            
        Returns:
            SearchResult: Kết quả tìm kiếm
        """
        try:
            if use_semantic:
                return self.elser_search.semantic_search(index_name, query)
            else:
                # Keyword search
                query_dsl = {
                    "query": {
                        "match": {
                            "message": query
                        }
                    }
                }
                return self.es_client.search_logs(index_name, query_dsl)
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm và phân tích logs: {str(e)}")
            return SearchResult(hits=[], total=0, took=0)
    
    def monitor_logs(self, index_name: str = "incident_logs",
                    interval: int = 60) -> None:
        """
        Monitor logs real-time
        
        Args:
            index_name (str): Tên index
            interval (int): Interval (giây)
        """
        try:
            logger.info(f"Bắt đầu monitor logs từ {index_name} mỗi {interval} giây...")
            
            import time
            
            while True:
                # Tìm kiếm logs gần đây
                query = {
                    "query": {
                        "range": {
                            "timestamp": {
                                "gte": "now-1m"
                            }
                        }
                    }
                }
                
                result = self.es_client.search_logs(index_name, query)
                
                if result.total > 0:
                    logger.info(f"Tìm thấy {result.total} logs mới:")
                    for hit in result.hits:
                        logger.info(f"  [{hit['level']}] {hit['service']}: {hit['message']}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Đã dừng monitor logs")
        except Exception as e:
            logger.error(f"Lỗi khi monitor logs: {str(e)}")