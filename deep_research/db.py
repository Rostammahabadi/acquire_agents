"""
Database utilities for deep research persistence.
"""

import hashlib
import json
from typing import Optional, Any
import psycopg2
import os
from psycopg2.extras import Json


def get_db_connection():
    """Get a database connection for deep research operations."""
    return psycopg2.connect(
        host="localhost",
        database="acquire_agents",
        user="acquire_user",
        password="acquire_pass",
        port=5432
    )


def persist_sector_research_record(
    business_id: Optional[str],
    sector_key: str,
    agent_type: str,
    research_run_id: str,
    version: int,
    agent_output: dict,
    model_name: str,
    prompt_version: str,
    sources: Optional[Any] = None,
    confidence_level: Optional[str] = None
) -> None:
    """
    Persist a sector research record to the database.

    Computes content_hash from sector_key + agent_type + prompt_version + agent_output.
    Relies on database unique constraint to prevent duplicates.
    """
    # Compute content hash
    content_to_hash = f"{sector_key}|{agent_type}|{prompt_version}|{json.dumps(agent_output, sort_keys=True)}"
    content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

    # Prepare data
    sources_json = Json(sources) if sources is not None else None

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO sector_research_records (
                    business_id, sector_key, agent_type, research_run_id,
                    version, content_hash, agent_output, model_name,
                    prompt_version, sources, confidence_level
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                business_id, sector_key, agent_type, research_run_id,
                version, content_hash, Json(agent_output), model_name,
                prompt_version, sources_json, confidence_level
            ))
        conn.commit()

    except psycopg2.errors.UniqueViolation:
        # Duplicate record - swallow the error and continue
        if conn:
            conn.rollback()
        pass  # Silently ignore duplicate inserts

    except Exception as e:
        # Other database errors - fail fast
        if conn:
            conn.rollback()
        raise e

    finally:
        if conn:
            conn.close()
