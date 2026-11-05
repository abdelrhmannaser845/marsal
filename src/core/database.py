import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.core.models import DispatchResult, DispatchStatus, DispatchChannel


class DispatchDatabase:
    """Manages SQLite audit log for all sent emails and WhatsApp messages."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dispatches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    student_name TEXT,
                    recipient TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message_preview TEXT,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_student_id ON dispatches(student_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON dispatches(timestamp)
            """)
            conn.commit()

    def log(
        self,
        result: DispatchResult,
        student_name: str = "",
        message_preview: str = ""
    ) -> int:
        """Insert dispatch log entry."""
        ts = result.timestamp or datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO dispatches (
                    timestamp, student_id, student_name, recipient, channel,
                    status, message_preview, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    result.student_id,
                    student_name,
                    result.recipient,
                    result.channel.value if isinstance(result.channel, DispatchChannel) else str(result.channel),
                    result.status.value if isinstance(result.status, DispatchStatus) else str(result.status),
                    message_preview or result.message_snippet,
                    result.error_message
                )
            )
            conn.commit()
            return cursor.lastrowid

    def get_history(self, limit: int = 50, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent dispatch records."""
        with self._get_connection() as conn:
            if channel:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, student_id, student_name, recipient, channel, status, message_preview, error_message
                    FROM dispatches
                    WHERE channel = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (channel, limit)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, student_id, student_name, recipient, channel, status, message_preview, error_message
                    FROM dispatches
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_summary(self) -> Dict[str, Any]:
        """Return total counts of success and failures."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) as skipped
                FROM dispatches
            """)
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "success": row["success"] or 0,
                "failed": row["failed"] or 0,
                "skipped": row["skipped"] or 0,
            }
