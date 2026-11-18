from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
import requests

from server import caddy_manager
from server.caddy_manager import CaddyManager


def make_archive(binary_name: str, contents: bytes = b"fake caddy executable") -> bytes:
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"nested/{binary_name}", contents)
        archive.writestr("nested/README.txt", "Caddy")
    return archive_bytes.getvalue()


class FakeResponse:
    def __init__(self, body: bytes, error: Exception | None = None):
        self.body = body
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.error:
            raise self.error

    def iter_content(self, chunk_size):
        yield self.body


@pytest.mark.parametrize(
    ("is_dev", "expected_name"),
    [(True, CaddyManager.DEV_CONFIG_NAME), (False, CaddyManager.PROD_CONFIG_NAME)],
)
def test_set_config_selects_config_and_records_path(tmp_path, is_dev, expected_name):
    manager = CaddyManager(tmp_path)
    dev_config = tmp_path / CaddyManager.DEV_CONFIG_NAME
    prod_config = tmp_path / CaddyManager.PROD_CONFIG_NAME
    dev_config.write_text("dev", encoding="utf-8")
    prod_config.write_text("prod", encoding="utf-8")

    selected = manager.set_config(is_dev)

    assert selected == tmp_path / expected_name
    assert manager.config_path == selected


def test_set_config_produces_both_configs_when_folder_is_empty(tmp_path):
    manager = CaddyManager(tmp_path / "Caddy")

    selected = manager.set_config(is_dev=True)

    dev_config = tmp_path / "Caddy" / CaddyManager.DEV_CONFIG_NAME
    prod_config = tmp_path / "Caddy" / CaddyManager.PROD_CONFIG_NAME
    assert selected == dev_config
    assert dev_config.read_text(encoding="utf-8") == CaddyManager.DEV_CONFIG_CONTENT
    assert prod_config.read_text(encoding="utf-8") == CaddyManager.PROD_CONFIG_CONTENT


def test_set_config_produces_only_missing_config_and_preserves_existing(tmp_path):
    manager = CaddyManager(tmp_path)
    existing = tmp_path / CaddyManager.DEV_CONFIG_NAME
    existing.write_text("user-edited dev config", encoding="utf-8")

    selected = manager.set_config(is_dev=False)

    assert selected == tmp_path / CaddyManager.PROD_CONFIG_NAME
    assert existing.read_text(encoding="utf-8") == "user-edited dev config"
    assert selected.read_text(encoding="utf-8") == CaddyManager.PROD_CONFIG_CONTENT


@pytest.mark.parametrize("invalid_value", [1, 0, "true", None])
def test_set_config_requires_a_bool(tmp_path, invalid_value):
    with pytest.raises(TypeError, match="is_dev must be a bool"):
        CaddyManager(tmp_path).set_config(invalid_value)


def test_supported_platforms_lists_site_targets_and_arm_variants():
    targets = CaddyManager.__supported_platforms__()

    assert len(targets) == 28
    assert ("linux", "arm", "5") in targets
    assert ("linux", "arm", "6") in targets
    assert ("linux", "arm", "7") in targets
    assert ("darwin", "arm64", None) in targets
    assert ("windows", "amd64", None) in targets


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Windows", "AMD64", ("windows", "amd64", None)),
        ("Linux", "x86_64", ("linux", "amd64", None)),
        ("Darwin", "aarch64", ("darwin", "arm64", None)),
        ("Linux", "armv7l", ("linux", "arm", "7")),
        ("Linux", "mips64el", ("linux", "mips64le", None)),
        ("DragonFly", "x86_64", ("dragonfly", "amd64", None)),
    ],
)
def test_download_for_current_platform_detects_target(
    tmp_path, monkeypatch, system, machine, expected
):
    manager = CaddyManager(tmp_path)
    calls = {}

    def fake_download(os_name, architecture, **kwargs):
        calls.update(os_name=os_name, architecture=architecture, **kwargs)
        return tmp_path / "downloaded-caddy"

    monkeypatch.setattr(caddy_manager.platform, "system", lambda: system)
    monkeypatch.setattr(caddy_manager.platform, "machine", lambda: machine)
    monkeypatch.setattr(manager, "__download_binary__", fake_download)

    result = manager.download_for_current_platform(
        modules=["github.com/example/module"], timeout=15
    )

    assert result == tmp_path / "downloaded-caddy"
    assert calls == {
        "os_name": expected[0],
        "architecture": expected[1],
        "arm_variant": expected[2],
        "modules": ["github.com/example/module"],
        "timeout": 15,
    }


@pytest.mark.parametrize(
    ("system", "machine", "message"),
    [
        ("Linux", "i686", "Unsupported CPU architecture"),
        ("Linux", "armv8l", "Unsupported ARM architecture"),
        ("Plan9", "x86_64", "Unsupported Caddy platform"),
    ],
)
def test_download_for_current_platform_rejects_unsupported_target(
    tmp_path, monkeypatch, system, machine, message
):
    monkeypatch.setattr(caddy_manager.platform, "system", lambda: system)
    monkeypatch.setattr(caddy_manager.platform, "machine", lambda: machine)

    with pytest.raises(ValueError, match=message):
        CaddyManager(tmp_path).download_for_current_platform()


def test_download_binary_extracts_windows_executable_and_builds_api_request(
    tmp_path, monkeypatch
):
    response = FakeResponse(make_archive("caddy.exe", b"windows binary"))
    request_args = {}

    def fake_get(url, **kwargs):
        request_args["url"] = url
        request_args.update(kwargs)
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    manager = CaddyManager(tmp_path)

    result = manager.__download_binary__("windows", "amd64")

    assert result == tmp_path / "caddy-windows-amd64.exe"
    assert result.read_bytes() == b"windows binary"
    assert request_args["url"] == CaddyManager.DOWNLOAD_URL
    assert request_args["params"] == [("os", "windows"), ("arch", "amd64")]
    assert request_args["stream"] is True


def test_download_binary_passes_arm_and_module_parameters(tmp_path, monkeypatch):
    request_args = {}

    def fake_get(url, **kwargs):
        request_args.update(url=url, **kwargs)
        return FakeResponse(make_archive("caddy"))

    monkeypatch.setattr(requests, "get", fake_get)

    result = CaddyManager(tmp_path).__download_binary__(
        "linux",
        "arm",
        arm_variant="7",
        modules=["github.com/caddy-dns/cloudflare@v1.2.3"],
    )

    assert result.name.startswith("caddy-linux-arm7-custom-")
    assert result.read_bytes() == b"fake caddy executable"
    assert request_args["params"] == [
        ("os", "linux"),
        ("arch", "arm"),
        ("arm", "7"),
        ("p", "github.com/caddy-dns/cloudflare@v1.2.3"),
    ]


def test_download_binary_writes_raw_response_body(tmp_path, monkeypatch):
    chmod_calls = []
    monkeypatch.setattr(requests, "get", lambda *_args, **_kwargs: FakeResponse(b"raw"))
    monkeypatch.setattr(Path, "chmod", lambda path, mode: chmod_calls.append(mode))

    result = CaddyManager(tmp_path).__download_binary__("linux", "amd64")

    assert result.read_bytes() == b"raw"
    assert len(chmod_calls) == 1
    assert chmod_calls[0] & 0o111 == 0o111


@pytest.mark.parametrize(
    ("os_name", "architecture", "arm_variant", "message"),
    [
        ("plan9", "amd64", None, "Unsupported Caddy platform"),
        ("linux", "arm", None, "requires arm_variant"),
        ("linux", "arm", "9", "Unsupported ARM variant"),
        ("linux", "amd64", "7", "Unsupported ARM variant"),
    ],
)
def test_download_binary_rejects_unsupported_targets_before_request(
    tmp_path, monkeypatch, os_name, architecture, arm_variant, message
):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("No request expected for invalid target"),
    )

    with pytest.raises(ValueError, match=message):
        CaddyManager(tmp_path).__download_binary__(
            os_name, architecture, arm_variant=arm_variant
        )


@pytest.mark.parametrize("modules", [[""], ["  "], [None]])
def test_download_binary_rejects_invalid_module_paths(tmp_path, monkeypatch, modules):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("No request expected for invalid module"),
    )

    with pytest.raises(ValueError, match="modules must contain non-empty"):
        CaddyManager(tmp_path).__download_binary__("linux", "amd64", modules=modules)


def test_download_binary_propagates_http_errors(tmp_path, monkeypatch):
    error = requests.HTTPError("not found")
    monkeypatch.setattr(
        requests, "get", lambda *_args, **_kwargs: FakeResponse(b"", error)
    )

    with pytest.raises(requests.HTTPError, match="not found"):
        CaddyManager(tmp_path).__download_binary__("linux", "amd64")


def test_download_binary_rejects_archive_without_executable(tmp_path, monkeypatch):
    archive = BytesIO()
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr("README.txt", "missing executable")
    monkeypatch.setattr(
        requests, "get", lambda *_args, **_kwargs: FakeResponse(archive.getvalue())
    )

    with pytest.raises(ValueError, match="did not contain its executable"):
        CaddyManager(tmp_path).__download_binary__("windows", "amd64")

    assert not list(tmp_path.glob("*.download"))

