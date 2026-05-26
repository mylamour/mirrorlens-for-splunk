from pathlib import Path

def test_docs_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "docs" / "video-script.md").exists()
    assert (root / "docs" / "submission-copy.md").exists()
