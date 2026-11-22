from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
import requests

from utils import caddy_manager
from utils.caddy_manager import CaddyManager

_test_threadpool = ThreadPoolExecutor(max_workers=1)


def manager_for(caddy_folder: Path) -> CaddyManager:
    manager = CaddyManager(threadpool=_test_threadpool)
    manager.caddy_folder = caddy_folder
    return manager


@pytest.fixture(scope="module", autouse=True)
def shutdown_test_threadpool():
    yield
    _test_threadpool.shutdown(wait=True)


class FakeProcess:
    def __init__(
        self,
        pid=1234,
        *,
        timeout_on_wait=False,
        stdout_output="",
        stderr_output="",
    ):
        self.pid = pid
        self.returncode = None
        self.timeout_on_wait = timeout_on_wait
        self.terminated = False
        self.killed = False
        self.stdout = StringIO(stdout_output)
        self.stderr = StringIO(stderr_output)

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if self.timeout_on_wait and not self.killed:
            raise caddy_manager.subprocess.TimeoutExpired("caddy-server", timeout)
        self.returncode = 0
        return self.returncode

    def kill(self):
        self.killed = True


def make_archive(binary_name: str, contents: bytes = b"fake caddy executable") -> bytes:
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"nested/{binary_name}", contents)
        archive.writestr("nested/README.txt", "Caddy")
    return archive_bytes.getvalue()


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        error: Exception | None = None,
        filename: str | None = "caddy_windows_amd64.exe",
    ):
        self.body = body
        self.error = error
        self.headers = (
            {"Content-Disposition": f'attachment; filename="{filename}"'}
            if filename
            else {}
        )
        self.iter_content_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.error:
            raise self.error

    def iter_content(self, chunk_size):
        self.iter_content_calls += 1
        yield self.body


@pytest.fixture(autouse=True)
def mock_download_metadata_and_get(monkeypatch):
    def fake_head(_url, **kwargs):
        parameters = dict(kwargs["params"])
        extension = ".exe" if parameters["os"] == "windows" else ""
        return FakeResponse(
            b"metadata only",
            filename=f"caddy_{parameters['os']}_{parameters['arch']}{extension}",
        )

    def fake_get(_url, **kwargs):
        parameters = dict(kwargs["params"])
        return FakeResponse(
            make_archive("caddy.exe" if parameters["os"] == "windows" else "caddy"),
            filename=f"caddy_{parameters['os']}_{parameters['arch']}"
            f"{'.exe' if parameters['os'] == 'windows' else ''}",
        )

    monkeypatch.setattr(requests, "head", fake_head)
    monkeypatch.setattr(requests, "get", fake_get)


@pytest.mark.parametrize(
    ("is_dev", "expected_name"),
    [(True, CaddyManager.DEV_CONFIG_NAME), (False, CaddyManager.PROD_CONFIG_NAME)],
)
def test_set_config_selects_and_records_path(tmp_path, is_dev, expected_name):
    manager = manager_for(tmp_path)
    dev_config = tmp_path / CaddyManager.DEV_CONFIG_NAME
    prod_config = tmp_path / CaddyManager.PROD_CONFIG_NAME
    dev_config.write_text("dev", encoding="utf-8")
    prod_config.write_text("prod", encoding="utf-8")

    selected = manager.set_config(is_dev)

    expected_path = tmp_path / expected_name
    assert selected == (True, str(expected_path))
    assert manager.config_path == expected_path


def test_set_config_produces_both_configs_when_folder_is_empty(tmp_path, monkeypatch):
    manager = manager_for(tmp_path / "Caddy")

    selected = manager.set_config(is_dev=True)

    dev_config = tmp_path / "Caddy" / CaddyManager.DEV_CONFIG_NAME
    prod_config = tmp_path / "Caddy" / CaddyManager.PROD_CONFIG_NAME
    assert selected == (True, str(dev_config))
    assert dev_config.read_text(encoding="utf-8") == CaddyManager.DEV_CONFIG_CONTENT
    assert prod_config.read_text(encoding="utf-8") == CaddyManager.PROD_CONFIG_CONTENT


def test_set_config_produces_only_missing_config_and_preserves_existing(
    tmp_path, monkeypatch
):
    manager = manager_for(tmp_path)
    existing = tmp_path / CaddyManager.DEV_CONFIG_NAME
    existing.write_text("user-edited dev config", encoding="utf-8")

    selected = manager.set_config(is_dev=False)

    assert selected == (True, str(tmp_path / CaddyManager.PROD_CONFIG_NAME))
    assert existing.read_text(encoding="utf-8") == "user-edited dev config"
    assert Path(selected[1]).read_text(encoding="utf-8") == CaddyManager.PROD_CONFIG_CONTENT


def test_set_config_returns_config_producer_failure(tmp_path, monkeypatch):
    manager = manager_for(tmp_path)
    monkeypatch.setattr(
        manager,
        "__produce_config_files__",
        lambda: (False, "configuration write failed"),
    )

    assert manager.set_config(is_dev=True) == (False, "configuration write failed")


def test_set_config_rejects_missing_files_after_producer_succeeds(tmp_path, monkeypatch):
    manager = manager_for(tmp_path)
    monkeypatch.setattr(
        manager,
        "__produce_config_files__",
        lambda: (True, "producer reported success"),
    )

    assert manager.set_config(is_dev=True) == (
        False,
        "Invalid Caddy configuration files",
    )


def test_start_server_runs_configured_executable_and_streams_output(
    tmp_path, monkeypatch
):
    manager = manager_for(tmp_path)
    config_path = tmp_path / CaddyManager.DEV_CONFIG_NAME
    config_path.write_text("dev", encoding="utf-8")
    manager.config_path = config_path
    executable_name = (
        "caddy-server.exe" if caddy_manager.platform.system().lower() == "windows"
        else "caddy-server"
    )
    executable_path = tmp_path / executable_name
    executable_path.write_bytes(b"fake executable")
    process = FakeProcess(stdout_output="server ready\n", stderr_output="test log\n")
    calls = []
    submitted = []
    original_submit = manager.threadpool.submit

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return process

    def fake_submit(function, *args, **kwargs):
        future = original_submit(function, *args, **kwargs)
        submitted.append((function, args, kwargs, future))
        return future

    monkeypatch.setattr(caddy_manager.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(manager.threadpool, "submit", fake_submit)

    result = manager.start_server()

    assert result == (True, "Caddy server started (PID: 1234)")
    assert manager.server_pid == 1234
    assert manager._server_process is process
    assert calls == [
        (
            [
                str(executable_path),
                "run",
                "--config",
                str(config_path),
                "--adapter",
                "caddyfile",
            ],
            {
                "cwd": tmp_path,
                "stdout": caddy_manager.subprocess.PIPE,
                "stderr": caddy_manager.subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "bufsize": 1,
            },
        )
    ]
    assert [submission[:3] for submission in submitted] == [
        (manager.caddy_logger, (process.stderr, process.stdout), {})
    ]
    submitted[0][3].result(timeout=1)

    log_contents = (tmp_path / "caddy_server_log.txt").read_text(encoding="utf-8")
    assert "Error: test log" in log_contents
    assert "Info: server ready" in log_contents


def test_start_server_requires_selected_config(tmp_path):
    assert manager_for(tmp_path).start_server() == (
        False,
        "Caddy configuration has not been set",
    )


def test_start_server_requires_executable(tmp_path):
    manager = manager_for(tmp_path)
    config_path = tmp_path / CaddyManager.DEV_CONFIG_NAME
    config_path.write_text("dev", encoding="utf-8")
    manager.config_path = config_path

    successful, message = manager.start_server()

    assert successful is False
    assert "Caddy executable does not exist" in message


def test_start_server_returns_launch_error(tmp_path, monkeypatch):
    manager = manager_for(tmp_path)
    config_path = tmp_path / CaddyManager.DEV_CONFIG_NAME
    config_path.write_text("dev", encoding="utf-8")
    manager.config_path = config_path
    executable_name = (
        "caddy-server.exe" if caddy_manager.platform.system().lower() == "windows"
        else "caddy-server"
    )
    (tmp_path / executable_name).write_bytes(b"fake executable")
    monkeypatch.setattr(
        caddy_manager.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("launch failed")),
    )

    assert manager.start_server() == (
        False,
        "Could not start Caddy server: launch failed",
    )
    assert manager.server_pid is None


def test_start_server_does_not_start_duplicate_process(tmp_path, monkeypatch):
    manager = manager_for(tmp_path)
    process = FakeProcess(pid=42)
    manager._server_process = process
    manager.server_pid = process.pid
    monkeypatch.setattr(
        caddy_manager.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("duplicate process should not start"),
    )

    assert manager.start_server() == (True, "Caddy server is already running (PID: 42)")


def test_shutdown_server_terminates_and_clears_process_state(tmp_path):
    manager = manager_for(tmp_path)
    process = FakeProcess(pid=42)
    manager._server_process = process
    manager.server_pid = process.pid

    result = manager.shutdown_server()

    assert result == (True, "Caddy server stopped (PID: 42)")
    assert process.terminated is True
    assert manager.server_pid is None
    assert manager._server_process is None


def test_shutdown_server_kills_process_that_does_not_stop(tmp_path):
    manager = manager_for(tmp_path)
    process = FakeProcess(pid=42, timeout_on_wait=True)
    manager._server_process = process
    manager.server_pid = process.pid

    result = manager.shutdown_server(timeout=0.01)

    assert result == (True, "Caddy server stopped (PID: 42)")
    assert process.terminated is True
    assert process.killed is True
    assert manager.server_pid is None


def test_shutdown_server_reports_when_not_running(tmp_path):
    assert manager_for(tmp_path).shutdown_server() == (
        False,
        "Caddy server is not running",
    )


def test_config_producer_returns_failure_when_file_write_fails(tmp_path, monkeypatch):
    def fail_write(*_args, **_kwargs):
        raise OSError("disk is read-only")

    monkeypatch.setattr(Path, "write_text", fail_write)

    result = manager_for(tmp_path).__produce_config_files__()

    assert result[0] is False
    assert "disk is read-only" in result[1]


@pytest.mark.parametrize("invalid_value", [1, 0, "true", None])
def test_set_config_requires_a_bool(tmp_path, invalid_value):
    assert manager_for(tmp_path).set_config(invalid_value) == (
        False,
        "is_dev must be a bool",
    )


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
    manager = manager_for(tmp_path)
    calls = {}

    def fake_download(os_name, architecture, **kwargs):
        calls.update(os_name=os_name, architecture=architecture, **kwargs)
        return True, str(tmp_path / "downloaded-caddy")

    monkeypatch.setattr(caddy_manager.platform, "system", lambda: system)
    monkeypatch.setattr(caddy_manager.platform, "machine", lambda: machine)
    monkeypatch.setattr(manager, "__download_binary__", fake_download)

    result = manager.download_for_current_platform(
        modules=["github.com/example/module"], timeout=15
    )

    assert result == (True, str(tmp_path / "downloaded-caddy"))
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

    result = manager_for(tmp_path).download_for_current_platform()
    assert result[0] is False
    assert message in result[1]


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
    manager = manager_for(tmp_path)

    successful, message = manager.__download_binary__("windows", "amd64")

    result = Path(message)
    assert successful is True
    assert result == tmp_path / "caddy-server.exe"
    assert result.read_bytes() == b"windows binary"
    assert request_args["url"] == CaddyManager.DOWNLOAD_URL
    assert request_args["params"] == [("os", "windows"), ("arch", "amd64")]
    assert request_args["stream"] is True
    assert not (tmp_path / "caddy_windows_amd64.exe").exists()


def test_download_binary_reuses_server_named_archive_without_reading_body(
    tmp_path, monkeypatch
):
    response = FakeResponse(make_archive("caddy.exe", b"cached binary"))
    get_calls = []

    def fake_get(*_args, **_kwargs):
        get_calls.append(True)
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    manager = manager_for(tmp_path)

    first_result = manager.__download_binary__("windows", "amd64")
    second_result = manager.__download_binary__("windows", "amd64")

    assert first_result == second_result
    assert first_result[0] is True
    assert Path(second_result[1]).read_bytes() == b"cached binary"
    assert response.iter_content_calls == 1
    assert len(get_calls) == 1
    assert len(list(tmp_path.glob("caddy*"))) == 1
    assert not list(tmp_path.glob(".caddy-download-*.name"))


def test_download_binary_requires_server_filename(tmp_path, monkeypatch):
    response = FakeResponse(b"", filename=None)
    monkeypatch.setattr(
        requests,
        "head",
        lambda *_args, **_kwargs: response,
    )

    successful, message = manager_for(tmp_path).__download_binary__("linux", "amd64")

    assert successful is False
    assert "did not provide a filename" in message
    assert response.iter_content_calls == 0


def test_download_binary_passes_arm_and_module_parameters(tmp_path, monkeypatch):
    request_args = {}

    def fake_get(url, **kwargs):
        request_args.update(url=url, **kwargs)
        return FakeResponse(make_archive("caddy"), filename="caddy_linux_arm")

    monkeypatch.setattr(requests, "get", fake_get)

    successful, message = manager_for(tmp_path).__download_binary__(
        "linux",
        "arm",
        arm_variant="7",
        modules=["github.com/caddy-dns/cloudflare@v1.2.3"],
    )

    result = Path(message)
    assert successful is True
    assert result.name == "caddy-server"
    assert result.read_bytes() == b"fake caddy executable"
    assert request_args["params"] == [
        ("os", "linux"),
        ("arch", "arm"),
        ("arm", "7"),
        ("p", "github.com/caddy-dns/cloudflare@v1.2.3"),
    ]


def test_download_binary_writes_raw_response_body(tmp_path, monkeypatch):
    chmod_calls = []
    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(b"raw", filename="caddy_linux_amd64"),
    )
    monkeypatch.setattr(Path, "chmod", lambda path, mode: chmod_calls.append(mode))

    successful, message = manager_for(tmp_path).__download_binary__("linux", "amd64")

    result = Path(message)
    assert successful is True
    assert result.read_bytes() == b"raw"
    assert len(chmod_calls) == 1
    assert chmod_calls[0] & 0o111 == 0o111


@pytest.mark.parametrize(
    ("os_name", "expected_name"),
    [("windows", "caddy-server.exe"), ("linux", "caddy-server")],
)
def test_download_binary_skips_all_requests_when_named_file_exists(
    tmp_path, monkeypatch, os_name, expected_name
):
    manager = manager_for(tmp_path)
    existing_binary = tmp_path / expected_name
    existing_binary.write_bytes(b"already downloaded")
    monkeypatch.setattr(
        requests,
        "head",
        lambda *_args, **_kwargs: pytest.fail("HEAD should not run for cached file"),
    )
    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("GET should not run for cached file"),
    )

    result = manager.__download_binary__(os_name, "amd64")

    assert result == (True, str(existing_binary))
    assert existing_binary.read_bytes() == b"already downloaded"


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

    result = manager_for(tmp_path).__download_binary__(
        os_name, architecture, arm_variant=arm_variant
    )
    assert result[0] is False
    assert message in result[1]


@pytest.mark.parametrize("modules", [[""], ["  "], [None]])
def test_download_binary_rejects_invalid_module_paths(tmp_path, monkeypatch, modules):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("No request expected for invalid module"),
    )

    result = manager_for(tmp_path).__download_binary__(
        "linux", "amd64", modules=modules
    )
    assert result[0] is False
    assert "modules must contain non-empty" in result[1]


def test_download_binary_propagates_http_errors(tmp_path, monkeypatch):
    error = requests.HTTPError("not found")
    monkeypatch.setattr(
        requests, "get", lambda *_args, **_kwargs: FakeResponse(b"", error)
    )

    result = manager_for(tmp_path).__download_binary__("linux", "amd64")
    assert result[0] is False
    assert "not found" in result[1]


def test_download_binary_rejects_archive_without_executable(tmp_path, monkeypatch):
    archive = BytesIO()
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr("README.txt", "missing executable")
    monkeypatch.setattr(
        requests, "get", lambda *_args, **_kwargs: FakeResponse(archive.getvalue())
    )

    result = manager_for(tmp_path).__download_binary__("windows", "amd64")
    assert result[0] is False
    assert "did not contain its executable" in result[1]

    assert not list(tmp_path.glob("*.download"))


