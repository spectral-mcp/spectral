"""Tests for APK patching via apk-mitm-python."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cli.commands.android.patch import patch_apk


async def _fake_run_apk_mitm(
    input_path: Path, output_path: Path, *, is_bundle: bool = False
) -> None:
    """Simulate _run_apk_mitm by prefixing the input content."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"patched-" + input_path.read_bytes())


class TestPatchApk:
    def test_patches_single_apk(self, tmp_path: Path) -> None:
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"fake-apk")
        output = tmp_path / "patched.apk"

        with patch("cli.commands.android.patch._run_apk_mitm", new=_fake_run_apk_mitm):
            result = patch_apk(apk, output)

        assert result == output
        assert output.read_bytes() == b"patched-fake-apk"

    def test_patches_apks_bundle(self, tmp_path: Path) -> None:
        bundle = tmp_path / "app.apks"
        bundle.write_bytes(b"fake-bundle")
        output = tmp_path / "patched.apks"

        with patch("cli.commands.android.patch._run_apk_mitm", new=_fake_run_apk_mitm):
            result = patch_apk(bundle, output)

        assert result == output
        assert output.read_bytes() == b"patched-fake-bundle"

    def test_detects_bundle_by_extension(self, tmp_path: Path) -> None:
        bundle = tmp_path / "app.apks"
        bundle.write_bytes(b"data")
        output = tmp_path / "out.apks"

        calls: list[bool] = []

        async def spy(
            input_path: Path, output_path: Path, *, is_bundle: bool = False
        ) -> None:
            calls.append(is_bundle)
            output_path.write_bytes(b"ok")

        with patch("cli.commands.android.patch._run_apk_mitm", new=spy):
            patch_apk(bundle, output)

        assert calls == [True]

    def test_single_apk_not_bundle(self, tmp_path: Path) -> None:
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"data")
        output = tmp_path / "out.apk"

        calls: list[bool] = []

        async def spy(
            input_path: Path, output_path: Path, *, is_bundle: bool = False
        ) -> None:
            calls.append(is_bundle)
            output_path.write_bytes(b"ok")

        with patch("cli.commands.android.patch._run_apk_mitm", new=spy):
            patch_apk(apk, output)

        assert calls == [False]
