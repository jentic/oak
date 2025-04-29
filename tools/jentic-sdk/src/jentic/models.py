from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Represents a reference to a file ID
class FileId(BaseModel):
    id: str


# Represents the detailed file entry
class FileEntry(BaseModel):
    id: str
    filename: str
    type: str
    content: Dict[str, Any]  # Content can be any valid JSON object


# Represents an API reference within a workflow
class APIReference(BaseModel):
    api_id: str
    api_name: str
    api_version: str


# Represents the file references associated with a workflow/operation, keyed by file type
class AssociatedFiles(BaseModel):
    arazzo: List[FileId] = []
    open_api: List[FileId] = []


# Represents a single workflow entry in the 'workflows' dictionary
class WorkflowEntry(BaseModel):
    workflow_id: str
    workflow_uuid: str
    name: str
    api_references: List[APIReference]
    files: AssociatedFiles


# Represents a single operation entry in the 'operations' dictionary
class OperationEntry(BaseModel):
    id: str
    api_version_id: str
    operation_id: str
    path: str
    method: str
    summary: Optional[str] = None
    files: AssociatedFiles


# The main response model
class GetFilesResponse(BaseModel):
    files: Dict[str, Dict[str, FileEntry]]  # FileType -> FileId -> FileEntry
    workflows: Dict[str, WorkflowEntry]  # WorkflowUUID -> WorkflowEntry
    operations: Optional[Dict[str, OperationEntry]] = None  # OperationUUID -> OperationEntry


# Represents the details needed to execute a specific workflow
class WorkflowExecutionDetails(BaseModel):
    arazzo_doc: Optional[Dict[str, Any]] = None
    source_descriptions: Dict[str, Dict[str, Any]] = {}
    friendly_workflow_id: Optional[str] = None


class ApiCapabilitySearchRequest(BaseModel):
    """Request model for API capability search."""

    capability_description: str
    keywords: list[str] | None = None
    max_results: int = 5


class BaseSearchResult(BaseModel):
    summary: str
    description: str
    match_score: float = 0.0


class WorkflowSearchResult(BaseSearchResult):
    workflow_id: str


class OperationSearchResult(BaseSearchResult):
    operation_uuid: str
    path: str
    method: str


class APISearchResults(BaseModel):
    workflows: list[WorkflowSearchResult]
    operations: list[OperationSearchResult]
