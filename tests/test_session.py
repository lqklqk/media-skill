import pytest
import tempfile
import os
from media_skill.session import Session, SessionManager


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def temp_data_dir(tmp_path):
    return str(tmp_path / "data_dir")


def test_add_and_retrieve_message(temp_db):
    session = Session(session_id="test-1", db_path=temp_db)
    session.add_message("user", "hello")
    session.add_message("assistant", "hi there")
    history = session.get_history()
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"
    session.close()


def test_add_media_ref(temp_db):
    session = Session(session_id="test-2", db_path=temp_db)
    ref = session.add_media_ref("image", "/path/to/img.png")
    assert ref == "img_001"
    assert session.get_media_ref(ref) == "/path/to/img.png"

    ref2 = session.add_media_ref("video", "/path/to/vid.mp4")
    assert ref2 == "vid_001"
    session.close()


def test_get_recent_media_refs(temp_db):
    session = Session(session_id="test-3", db_path=temp_db)
    session.add_media_ref("image", "/path/1.png")
    session.add_media_ref("image", "/path/2.png")
    session.add_media_ref("image", "/path/3.png")
    refs = session.get_recent_media_refs("image", 2)
    assert len(refs) == 2
    assert refs[0] == "img_003"
    assert refs[1] == "img_002"
    session.close()


def test_max_messages_trim(temp_db):
    session = Session(session_id="test-4", db_path=temp_db, max_messages=3)
    for i in range(5):
        session.add_message("user", f"msg {i}")
    history = session.get_history()
    assert len(history) == 3
    session.close()


def test_session_persistence(temp_db):
    session = Session(session_id="test-5", db_path=temp_db)
    session.add_message("user", "hello")
    session.add_media_ref("image", "/path/img.png")

    # Reload session from same db
    session2 = Session(session_id="test-5", db_path=temp_db)
    assert len(session2.get_history()) == 1
    assert session2.get_media_ref("img_001") == "/path/img.png"
    session.close()
    session2.close()


def test_default_session_auto_create(temp_data_dir):
    sm = SessionManager(data_dir=temp_data_dir)
    session = sm.get_or_create_session()
    assert session.session_id is not None
    sm.clear_default()


def test_named_session(temp_data_dir):
    sm = SessionManager(data_dir=temp_data_dir)
    session = sm.get_or_create_session(session_id="custom-123")
    assert session.session_id == "custom-123"
    sm.clear_session("custom-123")


def test_list_sessions(temp_data_dir):
    sm = SessionManager(data_dir=temp_data_dir)
    sm.get_or_create_session(session_id="sess-a")
    sm.get_or_create_session(session_id="sess-b")
    sessions = sm.list_sessions()
    assert "sess-a" in sessions
    assert "sess-b" in sessions
    sm.clear_session("sess-a")
    sm.clear_session("sess-b")
