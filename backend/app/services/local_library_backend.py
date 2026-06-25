import abc
from typing import Dict, Any, List, Optional
import os

class LocalLibraryBackend(abc.ABC):
    """
    Abstract interface for Local Library access.
    This hides whether the library is accessed directly on disk (Direct) or via a remote Agent (Agent).
    """
    
    @abc.abstractmethod
    def scan_library(self, source_dir: str, essence_dir: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def read_essence_file(self, essence_dir: str, book_id: str, file_key: str) -> Optional[str]:
        pass
        
    @abc.abstractmethod
    def get_book_index(self, essence_dir: str) -> List[Dict[str, Any]]:
        pass
        
    @abc.abstractmethod
    def get_task_status(self, book_id: str) -> Dict[str, Any]:
        pass

class DirectLocalLibraryBackend(LocalLibraryBackend):
    """
    Direct disk-based implementation for local deployment.
    (This delegates to the existing local_library_scanner and local_essence_writer_service)
    """
    def scan_library(self, source_dir: str, essence_dir: str) -> Dict[str, Any]:
        from backend.app.services.local_library_scanner import scan_local_library
        return scan_local_library(source_dir, essence_dir)

    def read_essence_file(self, essence_dir: str, book_id: str, file_key: str) -> Optional[str]:
        from backend.app.services.local_essence_writer_service import read_essence_file
        return read_essence_file(essence_dir, book_id, file_key)
        
    def get_book_index(self, essence_dir: str) -> List[Dict[str, Any]]:
        from backend.app.services.local_library_scanner import get_books
        return get_books(essence_dir)
        
    def get_task_status(self, book_id: str) -> Dict[str, Any]:
        from backend.app.services.local_absorption_task_manager import get_task_status
        return get_task_status(book_id)

class AgentLocalLibraryBackend(LocalLibraryBackend):
    """
    Agent-based implementation for future cloud deployment.
    This will interact with a local agent over HTTP/WebSocket.
    Currently a placeholder.
    """
    def __init__(self, agent_url: str):
        self.agent_url = agent_url

    def scan_library(self, source_dir: str, essence_dir: str) -> Dict[str, Any]:
        raise NotImplementedError("Agent backend is not yet implemented.")

    def read_essence_file(self, essence_dir: str, book_id: str, file_key: str) -> Optional[str]:
        raise NotImplementedError("Agent backend is not yet implemented.")
        
    def get_book_index(self, essence_dir: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Agent backend is not yet implemented.")
        
    def get_task_status(self, book_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Agent backend is not yet implemented.")

# Factory method to get the active backend
def get_local_library_backend() -> LocalLibraryBackend:
    # Default to direct backend to ensure local mode works
    return DirectLocalLibraryBackend()
