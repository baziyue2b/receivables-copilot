from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_without_uncaught_errors() -> None:
    script = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(script).run(timeout=30)

    assert not app.exception
    assert any("应收账款" in heading.value for heading in app.get("markdown"))
    assert len(app.metric) == 5
