from pathlib import Path

import pytest
from typer.testing import CliRunner

ISO_PATH = Path(__file__).parent.parent / "mock_iso" / "test.iso"


@pytest.fixture(scope="session")
def iso() -> Path:
    if not ISO_PATH.exists():
        pytest.skip("mock ISO not built — see the `iso` job in tests.yml")
    return ISO_PATH


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()