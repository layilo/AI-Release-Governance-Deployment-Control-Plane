from __future__ import annotations

from ai_release_control_plane.storage.filesystem import FileSystemStorage


def test_filesystem_storage_roundtrip(tmp_path):
    storage = FileSystemStorage(tmp_path)
    storage.put("x", "id1", {"a": 1})
    assert storage.get("x", "id1") == {"a": 1}
    assert len(storage.list("x")) == 1
    storage.delete("x", "id1")
    assert storage.get("x", "id1") is None
