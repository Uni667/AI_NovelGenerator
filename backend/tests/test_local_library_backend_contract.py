import pytest
import inspect
from backend.app.services.local_library_backend import (
    LocalLibraryBackend,
    DirectLocalLibraryBackend,
    AgentLocalLibraryBackend,
    get_local_library_backend
)

def test_direct_backend_conforms_to_contract():
    assert issubclass(DirectLocalLibraryBackend, LocalLibraryBackend)
    backend = get_local_library_backend()
    assert isinstance(backend, DirectLocalLibraryBackend)

def test_agent_backend_placeholder_exists():
    assert issubclass(AgentLocalLibraryBackend, LocalLibraryBackend)
    backend = AgentLocalLibraryBackend("http://localhost:8080")
    with pytest.raises(NotImplementedError):
        backend.scan_library("a", "b")

def test_interface_signature_stable():
    methods = ["scan_library", "read_essence_file", "get_book_index", "get_task_status"]
    for m in methods:
        assert hasattr(LocalLibraryBackend, m)
        sig = inspect.signature(getattr(LocalLibraryBackend, m))
        # Ensure signatures have the required parameters
        if m == "scan_library":
            assert "source_dir" in sig.parameters
            assert "essence_dir" in sig.parameters
        elif m == "read_essence_file":
            assert "essence_dir" in sig.parameters
            assert "book_id" in sig.parameters
            assert "file_key" in sig.parameters
        elif m == "get_book_index":
            assert "essence_dir" in sig.parameters
        elif m == "get_task_status":
            assert "book_id" in sig.parameters
