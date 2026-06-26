from cda_calc import upload_store as store


def test_save_and_load_tcx(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(store, "TCX_FILE", tmp_path / "ride.tcx")
    monkeypatch.setattr(store, "TCX_META", tmp_path / "ride.tcx.json")

    assert store.load_tcx() is None
    store.save_tcx(b"<tcx/>", "jazda.tcx")
    data, name = store.load_tcx()
    assert data == b"<tcx/>"
    assert name == "jazda.tcx"

    store.clear_tcx()
    assert store.load_tcx() is None


def test_save_and_load_splits(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(store, "SPLITS_FILE", tmp_path / "splits.csv")
    monkeypatch.setattr(store, "SPLITS_META", tmp_path / "splits.csv.json")

    store.save_splits(b"a,b\n1,2", "lapy.csv")
    data, name = store.load_splits()
    assert data == b"a,b\n1,2"
    assert name == "lapy.csv"

    store.clear_splits()
    assert store.load_splits() is None
