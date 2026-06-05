"""Session management for media skill context using SQLite."""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta


class Message:
    """Represents a single message in the conversation history."""

    def __init__(self, role: str, content: str, media: Optional[dict] = None):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.media = media  # {"type": "image"|"video", "ref": "img_001", "file_path": "..."}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "media": self.media,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        msg = cls(role=data["role"], content=data["content"], media=data.get("media"))
        msg.timestamp = data.get("timestamp", datetime.now().isoformat())
        return msg


class Session:
    """Manages conversation context for a single session."""

    def __init__(self, session_id: str, db_path: str, max_messages: int = 20):
        self.session_id = session_id
        self.db_path = db_path
        self.max_messages = max_messages
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        self._load()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                media TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS media_refs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ref_name TEXT NOT NULL,
                media_type TEXT NOT NULL,
                file_path TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def _load(self):
        rows = self._conn.execute(
            "SELECT role, content, media, timestamp FROM messages WHERE session_id = ? ORDER BY id",
            (self.session_id,)
        ).fetchall()
        self.messages = [
            Message.from_dict({
                "role": r[0],
                "content": r[1],
                "media": json.loads(r[2]) if r[2] else None,
                "timestamp": r[3],
            })
            for r in rows
        ]

        media_rows = self._conn.execute(
            "SELECT ref_name, media_type, file_path FROM media_refs WHERE session_id = ?",
            (self.session_id,)
        ).fetchall()
        self.media_refs = {r[0]: r[2] for r in media_rows}

    def _save(self):
        """No-op now that we write directly to DB in add_message."""
        pass

    def add_message(self, role: str, content: str, media: Optional[dict] = None):
        media_json = json.dumps(media) if media else None
        self._conn.execute(
            "INSERT INTO messages (session_id, role, content, media, timestamp) VALUES (?, ?, ?, ?, ?)",
            (self.session_id, role, content, media_json, datetime.now().isoformat())
        )
        self._conn.commit()
        # Update in-memory list
        self.messages.append(Message(role=role, content=content, media=media))
        self._trim()

    def _trim(self):
        if len(self.messages) > self.max_messages:
            excess = len(self.messages) - self.max_messages
            self._conn.execute(
                "DELETE FROM messages WHERE id IN (SELECT id FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?)",
                (self.session_id, excess)
            )
            self._conn.commit()
            # Keep in-memory list in sync
            self.messages = self.messages[-self.max_messages:]
        self._trim()

    def add_media_ref(self, media_type: str, file_path: str) -> str:
        """Add a reference to a generated/uploaded media file.

        Returns the reference name like 'img_001' or 'vid_002'.
        """
        counter = len([k for k in self.media_refs if k.startswith(media_type[:1])]) + 1
        prefix = "img" if media_type == "image" else "vid"
        ref_name = f"{prefix}_{counter:03d}"
        self._conn.execute(
            "INSERT INTO media_refs (session_id, ref_name, media_type, file_path) VALUES (?, ?, ?, ?)",
            (self.session_id, ref_name, media_type, file_path)
        )
        self._conn.commit()
        self.media_refs[ref_name] = file_path
        return ref_name

    def get_media_ref(self, ref_name: str) -> Optional[str]:
        """Get file path for a media reference."""
        return self.media_refs.get(ref_name)

    def get_history(self, limit: Optional[int] = None) -> list:
        """Get message history, optionally limited to last N messages."""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def get_recent_media_refs(self, media_type: str, count: int = 3) -> list:
        """Get most recent N media references of a type."""
        prefix = "img" if media_type == "image" else "vid"
        refs = [k for k in sorted(self.media_refs.keys(), reverse=True) if k.startswith(prefix)]
        return refs[:count]

    def _trim(self):
        if len(self.messages) > self.max_messages:
            excess = len(self.messages) - self.max_messages
            self._conn.execute(
                "DELETE FROM messages WHERE id IN (SELECT id FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?)",
                (self.session_id, excess)
            )
            self._conn.commit()
            # Keep in-memory list in sync
            self.messages = self.messages[-self.max_messages:]

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def clear(self):
        """Clear all session data."""
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
        self._conn.execute("DELETE FROM media_refs WHERE session_id = ?", (self.session_id,))
        self._conn.commit()
        self.messages = []
        self.media_refs = {}

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class SessionManager:
    """Manages multiple sessions using SQLite for persistence."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Use the skill package's directory for data storage
            skill_dir = Path(__file__).resolve().parent.parent
            data_dir = str(skill_dir / "data")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.data_dir / "sessions.db")
        self.state_file = str(self.data_dir / "state.json")
        self._default_session_id = self._load_state()
        self._known_sessions = set()

    def _load_state(self) -> str:
        if Path(self.state_file).exists():
            data = json.loads(Path(self.state_file).read_text(encoding="utf-8"))
            return data.get("default_session_id", None)
        return None

    def _save_state(self):
        data = {
            "default_session_id": self._default_session_id,
            "sessions": sorted(list(self._known_sessions)),
        }
        Path(self.state_file).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _register_session(self, session_id: str):
        """Track a session ID so list_sessions can find it."""
        self._known_sessions.add(session_id)
        self._save_state()

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get or create a session.

        If session_id is None, uses the default session (auto-created on first use).
        """
        if session_id is None:
            if self._default_session_id is None:
                self._default_session_id = str(uuid.uuid4())
                self._save_state()
            session_id = self._default_session_id
        self._register_session(session_id)
        return Session(session_id=session_id, db_path=self.db_path)

    def list_sessions(self) -> list:
        """List all session IDs."""
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT DISTINCT session_id FROM messages").fetchall()
            disk_sessions = set(r[0] for r in rows)
            conn.close()
        except sqlite3.OperationalError:
            disk_sessions = set()
        if self._default_session_id:
            disk_sessions.add(self._default_session_id)
        return sorted(disk_sessions | self._known_sessions)

    def clear_session(self, session_id: str):
        """Clear a specific session."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM media_refs WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def clear_default(self):
        """Clear the default session."""
        if self._default_session_id:
            self.clear_session(self._default_session_id)
            self._default_session_id = None
            self._save_state()

    def clear_expired(self, max_age_days: int = 7):
        """Clear sessions older than max_age_days."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        try:
            conn = sqlite3.connect(self.db_path)
            cutoff_str = cutoff.isoformat()
            conn.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (cutoff_str,)
            )
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass
