import json
from datetime import datetime

from jrdev.messages.thread import MessageThread
from jrdev.messages import thread as thread_module


def _read_persisted_thread(thread_dir, thread_id):
    with open(thread_dir / f"{thread_id}.json") as f:
        return json.load(f)


def test_add_message_persists_and_updates_last_modified(tmp_path, monkeypatch):
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir()
    monkeypatch.setattr(thread_module, "THREADS_DIR", str(threads_dir))

    msg_thread = MessageThread("thread_add_message")
    old_modified = datetime(2000, 1, 1)
    msg_thread.metadata["last_modified"] = old_modified

    msg_thread.add_message("user", "hello", model="test-model", metadata={"source": "test"})

    assert msg_thread.messages == [
        {
            "role": "user",
            "content": "hello",
            "model": "test-model",
            "metadata": {"source": "test"},
        }
    ]
    assert msg_thread.metadata["last_modified"] > old_modified

    persisted = _read_persisted_thread(threads_dir, msg_thread.thread_id)
    assert persisted["messages"] == msg_thread.messages
    assert persisted["metadata"]["last_modified"] != old_modified.isoformat()


def test_clear_persists_empty_message_and_context_state(tmp_path, monkeypatch):
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir()
    monkeypatch.setattr(thread_module, "THREADS_DIR", str(threads_dir))

    msg_thread = MessageThread("thread_clear")
    old_modified = datetime(2000, 1, 1)
    msg_thread.messages = [{"role": "user", "content": "hello"}]
    msg_thread.context = {"src/example.py"}
    msg_thread.embedded_files = {"src/old.py"}
    msg_thread.metadata["last_modified"] = old_modified

    msg_thread.clear()

    assert msg_thread.messages == []
    assert msg_thread.context == set()
    assert msg_thread.embedded_files == set()
    assert msg_thread.metadata["last_modified"] > old_modified

    persisted = _read_persisted_thread(threads_dir, msg_thread.thread_id)
    assert persisted["messages"] == []
    assert persisted["context"] == []
    assert persisted["embedded_files"] == []
    assert persisted["metadata"]["last_modified"] != old_modified.isoformat()
