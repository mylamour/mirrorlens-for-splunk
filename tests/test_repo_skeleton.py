from pathlib import Path

def test_repo_skeleton_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "README.md").exists()
    assert (root / "LICENSE").exists()
    assert (root / "architecture_diagram.md").exists()
    assert (root / ".env.example").exists()
