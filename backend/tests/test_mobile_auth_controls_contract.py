from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MAIN_SOURCE = REPOSITORY_ROOT / "frontend" / "src" / "main.tsx"
MOBILE_AUTH_STYLES = REPOSITORY_ROOT / "frontend" / "src" / "mobileAuthControls.css"


def test_mobile_auth_controls_override_is_loaded_after_global_styles() -> None:
    source = MAIN_SOURCE.read_text(encoding="utf-8")

    assert source.index('import "./styles.css";') < source.index(
        'import "./mobileAuthControls.css";'
    )


def test_mobile_auth_controls_return_to_document_flow() -> None:
    source = MOBILE_AUTH_STYLES.read_text(encoding="utf-8")

    assert "@media (max-width: 560px)" in source
    assert ".marketlens-auth-controls" in source
    assert "position: static;" in source
    assert "width: min(1180px, calc(100% - 32px));" in source
    assert "margin: 16px auto 0;" in source
    assert "justify-content: flex-end;" in source
    assert "position: fixed;" not in source
