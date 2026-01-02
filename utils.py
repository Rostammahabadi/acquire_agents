"""
Agent execution logging utilities.

Provides functions to log agent execution status, errors, and metadata
for monitoring and debugging long-running background processes.
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
from database import get_session_sync
from models import AgentExecutionLog


@contextmanager
def log_agent_execution(
    agent_name: str,
    business_id: Optional[str] = None,
    input_snapshot: Optional[Dict[str, Any]] = None,
    execution_id: Optional[str] = None
):
    """
    Context manager for logging agent execution.

    Usage:
        with log_agent_execution("market_structure", business_id="123") as logger:
            # Do agent work
            result = some_llm_call()
            logger.log_success({"tokens_used": 1500})
    """
    if not execution_id:
        import uuid
        execution_id = str(uuid.uuid4())[:8]

    session = get_session_sync()
    start_time = time.time()

    # Create execution log entry
    log_entry = AgentExecutionLog(
        agent_name=agent_name,
        business_id=business_id,
        execution_id=execution_id,
        input_snapshot=input_snapshot or {},
        status="running",
        started_at=datetime.utcnow()
    )

    try:
        session.add(log_entry)
        session.commit()

        # Yield a logger object for the context
        logger = AgentLogger(log_entry, session)
        yield logger

        # If we get here, execution completed successfully
        if logger.final_status == "success":
            logger._finalize(success=True)
        else:
            # If not explicitly marked as success, assume it completed without explicit logging
            logger._finalize(success=True)

    except Exception as e:
        # Execution failed
        log_entry.status = "failure"
        log_entry.error_message = str(e)
        log_entry.completed_at = datetime.utcnow()
        log_entry.execution_metadata = {
            **(log_entry.execution_metadata or {}),
            "execution_time_seconds": time.time() - start_time
        }
        session.commit()
        raise
    finally:
        session.close()


class AgentLogger:
    """Logger object returned by log_agent_execution context manager."""

    def __init__(self, log_entry: AgentExecutionLog, session: Any):
        self.log_entry = log_entry
        self.session = session
        self.final_status = None
        self._pending_metadata = {}  # Store metadata updates until finalization

    def log_success(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark execution as successful with optional metadata."""
        self.final_status = "success"
        # Store metadata to be applied during finalization
        self._pending_metadata.update(metadata or {})

    def log_failure(self, error_message: str, metadata: Optional[Dict[str, Any]] = None):
        """Mark execution as failed with error message and optional metadata."""
        self.final_status = "failure"
        self.log_entry.status = "failure"
        self.log_entry.error_message = error_message
        # Store metadata to be applied during finalization
        self._pending_metadata.update(metadata or {})

    def log_partial(self, error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Mark execution as partially successful with optional error and metadata."""
        self.final_status = "partial"
        self.log_entry.status = "partial"
        if error_message:
            self.log_entry.error_message = error_message
        # Store metadata to be applied during finalization
        self._pending_metadata.update(metadata or {})

    def log_timeout(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark execution as timed out."""
        self.final_status = "timeout"
        self.log_entry.status = "timeout"
        # Store metadata to be applied during finalization
        self._pending_metadata.update(metadata or {})

    def _finalize(self, success: bool = True):
        """Finalize the log entry."""
        self.log_entry.completed_at = datetime.utcnow()
        execution_time = (self.log_entry.completed_at - self.log_entry.started_at).total_seconds()

        if success and self.final_status:
            self.log_entry.status = self.final_status
        elif success:
            self.log_entry.status = "success"

        # Apply any pending metadata updates
        current_metadata = self.log_entry.execution_metadata or {}
        self.log_entry.execution_metadata = {
            **current_metadata,
            **self._pending_metadata,
            "execution_time_seconds": execution_time
        }

        try:
            # Try to commit with existing session
            self.session.commit()
        except Exception as e:
            # If session is detached, create a new session and update
            if "DetachedInstanceError" in str(e):
                print(f"[LOGGER] Session detached, creating new session for finalization")
                new_session = get_session_sync()
                try:
                    # Re-attach the log entry to the new session
                    new_session.merge(self.log_entry)
                    new_session.commit()
                finally:
                    new_session.close()
            else:
                # Re-raise other exceptions
                raise


def log_agent_success(
    agent_name: str,
    business_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    input_snapshot: Optional[Dict[str, Any]] = None,
    execution_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log a successful agent execution.

    Returns the execution_id used for the log.
    """
    if not execution_id:
        import uuid
        execution_id = str(uuid.uuid4())[:8]

    session = get_session_sync()
    try:
        log_entry = AgentExecutionLog(
            agent_name=agent_name,
            business_id=business_id,
            execution_id=execution_id,
            input_snapshot=input_snapshot or {},
            status="success",
            execution_metadata=execution_metadata or {},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        session.add(log_entry)
        session.commit()
        return execution_id
    finally:
        session.close()


def log_agent_failure(
    agent_name: str,
    error_message: str,
    business_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    input_snapshot: Optional[Dict[str, Any]] = None,
    execution_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log a failed agent execution.

    Returns the execution_id used for the log.
    """
    if not execution_id:
        import uuid
        execution_id = str(uuid.uuid4())[:8]

    session = get_session_sync()
    try:
        log_entry = AgentExecutionLog(
            agent_name=agent_name,
            business_id=business_id,
            execution_id=execution_id,
            input_snapshot=input_snapshot or {},
            status="failure",
            error_message=error_message,
            execution_metadata=execution_metadata or {},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        session.add(log_entry)
        session.commit()
        return execution_id
    finally:
        session.close()
