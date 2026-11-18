"""Download official Caddy binaries for the platforms offered by caddyserver.com."""

from __future__ import annotations

import hashlib
import platform
import shutil
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

import requests


class CaddyManager:
    DOWNLOAD_URL = "https://caddyserver.com/api/download"
    DEV_CONFIG_NAME = "Caddyfile-dev.caddy"
    PROD_CONFIG_NAME = "Caddyfile-prod.caddy"
    DEV_CONFIG_CONTENT = """{\n    local_certs\n}\n\nlocalhost:8443 {\n    tls internal\n    reverse_proxy 127.0.0.1:80\n}\n"""
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

    def __init__(self, caddy_folder: str | Path | None = None):
        self.caddy_folder = (
            Path(caddy_folder)
            if caddy_folder is not None
            else Path(__file__).resolve().parent.parent / "Caddy"
        )
        self.config_path: Path | None = None

    def set_config(self, is_dev: bool) -> Path:
        """Select and return the dev or production Caddyfile path.

        When either managed configuration is missing, produce the missing
        config file(s) with one call to :meth:`produce_config_files`.
        """
        if not isinstance(is_dev, bool):
            raise TypeError("is_dev must be a bool")

        dev_config = self.caddy_folder / self.DEV_CONFIG_NAME
        prod_config = self.caddy_folder / self.PROD_CONFIG_NAME
        if not dev_config.is_file() or not prod_config.is_file():
            self.__produce_config_files__()

        self.config_path = dev_config if is_dev else prod_config
        return self.config_path

    def __produce_config_files__(self) -> None:
        """Create any missing dev and production Caddyfiles without overwriting."""
        self.caddy_folder.mkdir(parents=True, exist_ok=True)
        for filename, contents in (
            (self.DEV_CONFIG_NAME, self.DEV_CONFIG_CONTENT),
            (self.PROD_CONFIG_NAME, self.PROD_CONFIG_CONTENT),
        ):
            config_path = self.caddy_folder / filename
            if not config_path.exists():
                config_path.write_text(contents, encoding="utf-8")

    def download_for_current_platform(
        self,
        *,
        modules: Iterable[str] = (),
        timeout: float = 120,
    ) -> Path:
        """Download the Caddy binary matching the current OS and CPU architecture."""
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
                raise ValueError(f"Unsupported ARM architecture: {machine}")
        elif machine in architecture_aliases:
            architecture = architecture_aliases[machine]
        else:
            raise ValueError(f"Unsupported CPU architecture: {machine}")

        return self.__download_binary__(
            os_name,
            architecture,
            arm_variant=arm_variant,
            modules=modules,
            timeout=timeout,
        )

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
    ) -> Path:
        """Download a Caddy build and return its executable path.

        ``os_name`` and ``architecture`` use the API values listed by
        :meth:`supported_platforms` (for example ``("linux", "amd64")``).
        Optional ``modules`` are Go module paths, optionally suffixed with
        ``@version``, as accepted by Caddy's download page.
        """
        self.__validate_target__(os_name, architecture, arm_variant)
        module_list = tuple(modules)
        if any(
            not isinstance(module, str) or not module.strip() for module in module_list
        ):
            raise ValueError("modules must contain non-empty Go module paths")

        params: list[tuple[str, str]] = [("os", os_name), ("arch", architecture)]
        if arm_variant is not None:
            params.append(("arm", arm_variant))
        params.extend(("p", module.strip()) for module in module_list)

        self.caddy_folder.mkdir(parents=True, exist_ok=True)
        executable_name = "caddy.exe" if os_name == "windows" else "caddy"
        module_suffix = ""
        if module_list:
            digest = hashlib.sha256("\n".join(module_list).encode("utf-8")).hexdigest()[
                :10
            ]
            module_suffix = f"-custom-{digest}"
        output = self.caddy_folder / (
            f"caddy-{os_name}-{architecture}{arm_variant or ''}{module_suffix}"
            f"{'.exe' if executable_name.endswith('.exe') else ''}"
        )

        with requests.get(
            self.DOWNLOAD_URL, params=params, stream=True, timeout=timeout
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
                temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        if os_name != "windows":
            output.chmod(output.stat().st_mode | 0o111)
        return output

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
