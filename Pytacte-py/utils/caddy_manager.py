"""Download official Caddy binaries for the platforms offered by caddyserver.com."""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Iterable
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import UTC, datetime
from email.message import Message
from io import TextIOBase
from pathlib import Path

import requests


class CaddyManager:
    DOWNLOAD_URL = "https://caddyserver.com/api/download"
    DEV_CONFIG_NAME = "Caddyfile-dev.caddy"
    PROD_CONFIG_NAME = "Caddyfile-prod.caddy"
    DEV_CONFIG_CONTENT = """{\n    local_certs\n}\n\n127.0.0.1:8443 {\n    tls internal\n    reverse_proxy 127.0.0.1:80\n}\n"""
    PROD_CONFIG_CONTENT = """{\n    email admin@example.com\n    renewal_window_ratio 0.5\n}\n\nYOUR_PUBLIC_IPV4 {\n    tls {\n        issuer acme https://acme-v02.api.letsencrypt.org/directory {\n            profile shortlived\n        }\n    }\n\n    reverse_proxy 127.0.0.1:5000\n}\n"""
    
    PLATFORMS: dict[str, tuple[str, ...]] = {  # noqa: RUF012
        "dragonfly": ("amd64",),
        "freebsd": ("amd64", "arm", "arm64"),
        "linux": (
            "amd64", "arm", "arm64", "mips", "mips64", "mips64le",
            "mipsle", "ppc64", "ppc64le", "s390x", "loong64",
        ),
        "darwin": ("amd64", "arm64"),
        "openbsd": ("amd64", "arm", "arm64"),
        "windows": ("amd64", "arm", "arm64"),
    }
    ARM_VARIANTS: dict[str, tuple[str, ...]] = {  # noqa: RUF012
        "freebsd": ("6", "7"),
        "linux": ("5", "6", "7"),
        "openbsd": ("6", "7"),
        "windows": ("6", "7"),
    }

    def __init__(self, threadpool: ThreadPoolExecutor):
        self.caddy_folder = Path(__file__).resolve().parent.parent / "Caddy"
        self.config_path: Path | None = None
        self.server_pid: int | None = None
        self._server_process: subprocess.Popen | None = None
        self.threadpool = threadpool

    def caddy_logger(self, stderr: TextIOBase, stout: TextIOBase) -> None:
        """Continuously copy Caddy's stderr to the error log until the pipe closes."""
        log_path = self.caddy_folder / "caddy_server_log.txt"
        with log_path.open("a", encoding="utf-8") as log_file:
            
            log_file.write('\n_________________________________________\n')
            log_file.flush()
            
            for line in stderr:
                log_file.write(f'--> [ {datetime.now(UTC)} ) [ Error: {line} ]')
                log_file.flush()
            for line in stout:
                log_file.write(f'--> [ {datetime.now(UTC)} ) [ Info: {line} ]')
                log_file.flush()
            
            log_file.write('\n_________________________________________\n')
            log_file.flush()

    def set_config(self, is_dev: bool) -> tuple[bool, str]:
        """Select the dev or production Caddyfile and report its path."""

        if not isinstance(is_dev, bool):
            return False, "is_dev must be a bool"

        dev_config = self.caddy_folder / self.DEV_CONFIG_NAME
        prod_config = self.caddy_folder / self.PROD_CONFIG_NAME
        if not dev_config.is_file() or not prod_config.is_file():
            is_successful, message = self.__produce_config_files__()
            if not is_successful:
                return False, message

        if not dev_config.is_file() or not prod_config.is_file():
            return False, "Invalid Caddy configuration files"

        self.config_path = dev_config if is_dev else prod_config
        return True, str(self.config_path)

    def start_server(self) -> tuple[bool, str]:
        """Start Caddy with the configuration selected by :meth:`set_config`."""
        if self._server_process is not None:
            if self._server_process.poll() is None:
                self.server_pid = self._server_process.pid
                return True, f"Caddy server is already running (PID: {self.server_pid})"
            self._server_process = None
            self.server_pid = None

        if self.config_path is None or not self.config_path.is_file():
            return False, "Caddy configuration has not been set"

        executable_name = (
            "caddy-server.exe" if platform.system().lower() == "windows" else "caddy-server"
        )
        executable_path = self.caddy_folder / executable_name
        if not executable_path.is_file():
            return False, f"Caddy executable does not exist: {executable_path}"

        try:
            process = subprocess.Popen(
                [
                    str(executable_path),
                    "run",
                    "--config",
                    str(self.config_path),
                    "--adapter",
                    "caddyfile",
                ],
                cwd=self.caddy_folder,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as error:
            return False, f"Could not start Caddy server: {error}"

        self._server_process = process
        self.server_pid = process.pid
        if process.stderr is not None:
            self.threadpool.submit(self.caddy_logger, process.stderr, process.stdout)
        return True, f"Caddy server started (PID: {self.server_pid})"

    def shutdown_server(self, timeout: float = 10) -> tuple[bool, str]:
        """Stop the Caddy process started by this manager instance."""
        process = self._server_process
        if self.server_pid is None or process is None:
            return False, "Caddy server is not running"

        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        except OSError as error:
            return False, f"Could not stop Caddy server (PID: {self.server_pid}): {error}"

        stopped_pid = self.server_pid
        self.server_pid = None
        self._server_process = None
        return True, f"Caddy server stopped (PID: {stopped_pid})"

    def __produce_config_files__(self) -> tuple[bool, str]:
        """Create any missing dev and production Caddyfiles without overwriting."""
        try:
            self.caddy_folder.mkdir(parents=True, exist_ok=True)
            for filename, contents in (
                (self.DEV_CONFIG_NAME, self.DEV_CONFIG_CONTENT),
                (self.PROD_CONFIG_NAME, self.PROD_CONFIG_CONTENT),
            ):
                config_path = self.caddy_folder / filename
                if not config_path.exists():
                    config_path.write_text(contents, encoding="utf-8")
        except OSError as error:
            return False, f"Could not create Caddy configuration files: {error}"
        return True, "Caddy configuration files are ready"

    def download_for_current_platform(
        self,
        *,
        modules: Iterable[str] = (),
        timeout: float = 120,
    ) -> tuple[bool, str]:
        """Download the Caddy binary matching the current OS and CPU architecture."""
        try:
            operating_system = platform.system().lower()
            os_aliases = {
                "macos": "darwin",
                "mac os": "darwin",
                "dragonflybsd": "dragonfly",
            }
            os_name = os_aliases.get(operating_system, operating_system)

            machine = platform.machine().lower()
            architecture_aliases = {
                "amd64": "amd64",
                "x86_64": "amd64",
                "x64": "amd64",
                "arm64": "arm64",
                "aarch64": "arm64",
                "mips": "mips",
                "mips64": "mips64",
                "mipsel": "mipsle",
                "mips64el": "mips64le",
                "ppc64": "ppc64",
                "powerpc64": "ppc64",
                "ppc64le": "ppc64le",
                "powerpc64le": "ppc64le",
                "s390x": "s390x",
                "loongarch64": "loong64",
                "loong64": "loong64",
            }
            arm_variant = None
            if machine.startswith("armv"):
                variant = machine[4:5]
                if variant in {"5", "6", "7"}:
                    architecture = "arm"
                    arm_variant = variant
                else:
                    return False, f"Unsupported ARM architecture: {machine}"
            elif machine in architecture_aliases:
                architecture = architecture_aliases[machine]
            else:
                return False, f"Unsupported CPU architecture: {machine}"

            return self.__download_binary__(
                os_name,
                architecture,
                arm_variant=arm_variant,
                modules=modules,
                timeout=timeout,
            )
        except Exception as error:
            return False, str(error)

    @classmethod
    def __supported_platforms__(cls) -> tuple[tuple[str, str, str | None], ...]:
        """Return API OS/architecture pairs and ARM variants shown on the site."""
        targets = []
        for os_name, architectures in cls.PLATFORMS.items():
            for architecture in architectures:
                variants = (
                    cls.ARM_VARIANTS.get(os_name, ()) if architecture == "arm" else ()
                )
                if variants:
                    targets.extend(
                        (os_name, architecture, variant) for variant in variants
                    )
                else:
                    targets.append((os_name, architecture, None))
        return tuple(targets)

    def __download_binary__(
        self,
        os_name: str,
        architecture: str,
        *,
        arm_variant: str | None = None,
        modules: Iterable[str] = (),
        timeout: float = 120,
    ) -> tuple[bool, str]:
        """Download a Caddy build and report the executable path or error."""
        try:
            self.__validate_target__(os_name, architecture, arm_variant)
            module_list = tuple(modules)
            if any(
                not isinstance(module, str) or not module.strip()
                for module in module_list
            ):
                raise ValueError("modules must contain non-empty Go module paths")

            params: list[tuple[str, str]] = [("os", os_name), ("arch", architecture)]
            if arm_variant is not None:
                params.append(("arm", arm_variant))
            params.extend(("p", module.strip()) for module in module_list)

            executable_name = "caddy.exe" if os_name == "windows" else "caddy"
            output = self.caddy_folder / (
                f"caddy-server{'.exe' if os_name == 'windows' else ''}"
            )

            self.caddy_folder.mkdir(parents=True, exist_ok=True)
            if output.is_file():
                if os_name != "windows":
                    output.chmod(output.stat().st_mode | 0o111)
                return True, str(output)

            with requests.head(
                self.DOWNLOAD_URL,
                params=params,
                allow_redirects=True,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                disposition = Message()
                disposition["Content-Disposition"] = response.headers.get(
                    "Content-Disposition", ""
                )
                server_filename = disposition.get_filename()
                if not server_filename:
                    raise ValueError(
                        "Caddy download response did not provide a filename"
                    )

                # Treat the name as one local path component.
                server_filename = server_filename.replace("\\", "/").rsplit("/", 1)[-1]
                if server_filename in {"", ".", ".."}:
                    raise ValueError(
                        "Caddy download response provided an invalid filename"
                    )

            with requests.get(
                self.DOWNLOAD_URL,
                params=params,
                stream=True,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                    dir=self.caddy_folder, suffix=".download", delete=False
                ) as temp_file:
                    temp_path = Path(temp_file.name)
                    try:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                temp_file.write(chunk)
                    except Exception:
                        temp_path.unlink(missing_ok=True)
                        raise

            try:
                if zipfile.is_zipfile(temp_path):
                    with zipfile.ZipFile(temp_path) as archive:
                        binary_member = next(
                            (
                                name
                                for name in archive.namelist()
                                if Path(name).name.lower() == executable_name.lower()
                            ),
                            None,
                        )
                        if binary_member is None:
                            raise ValueError(
                                "Caddy download archive did not contain its executable"
                            )
                        with (
                            archive.open(binary_member) as source,
                            output.open("wb") as destination,
                        ):
                            shutil.copyfileobj(source, destination)
                else:
                    shutil.move(str(temp_path), str(output))
            finally:
                temp_path.unlink(missing_ok=True)

            if os_name != "windows":
                output.chmod(output.stat().st_mode | 0o111)
            return True, str(output)
        except Exception as error:
            return False, str(error)

    @classmethod
    def __validate_target__(
        cls, os_name: str, architecture: str, arm_variant: str | None
    ) -> None:
        if os_name not in cls.PLATFORMS or architecture not in cls.PLATFORMS[os_name]:
            raise ValueError(f"Unsupported Caddy platform: {os_name}/{architecture}")
        allowed_variants = (
            cls.ARM_VARIANTS.get(os_name, ()) if architecture == "arm" else ()
        )
        if arm_variant is not None and arm_variant not in allowed_variants:
            raise ValueError(f"Unsupported ARM variant for {os_name}: {arm_variant}")
        if allowed_variants and arm_variant is None:
            raise ValueError(
                f"{os_name}/arm requires arm_variant (one of {', '.join(allowed_variants)})"
            )
