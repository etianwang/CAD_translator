"""Build one macOS app containing the matching official read-only ODA DMG."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_APP = ROOT / "dist" / "Honsen CAD Translator.app"
VERSION = "1.8.8"
APP_EXECUTABLE = OUTPUT_APP / "Contents" / "MacOS" / f"Honsen_CAD_Translator_v{VERSION}"
ODA_DMG_RESOURCE = OUTPUT_APP / "Contents" / "Resources" / "ODAFileConverter.dmg"
ODA_EXECUTABLE = Path("Contents/MacOS/ODAFileConverter")


def run(*command: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def architectures(binary: Path) -> set[str]:
    output = subprocess.check_output(["lipo", "-archs", str(binary)], text=True)
    return set(output.strip().split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oda-dmg", required=True, type=Path, help="Official ODA macOS DMG matching the build architecture")
    parser.add_argument("--identity", default="-", help="Developer ID Application identity; '-' creates a local ad-hoc signature")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--dmg", action="store_true", help="Create a compressed distributable DMG after building the app")
    parser.add_argument("--dmg-output", type=Path, help="DMG output path (requires --dmg)")
    args = parser.parse_args()

    dmg = args.oda_dmg.expanduser().resolve()
    if not dmg.is_file() or dmg.suffix.lower() != ".dmg":
        raise SystemExit(f"ODA DMG does not exist: {dmg}")

    if not args.skip_frontend:
        run("npm", "ci", cwd=ROOT / "frontend")
        run("npm", "run", "build", cwd=ROOT / "frontend")

    build_env = os.environ.copy()
    if args.identity != "-":
        build_env["MACOS_CODESIGN_IDENTITY"] = args.identity
    else:
        build_env.pop("MACOS_CODESIGN_IDENTITY", None)
    run(
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        f"Honsen_CAD_Translator_v{VERSION}_macos.spec",
        env=build_env,
    )
    if not APP_EXECUTABLE.is_file():
        raise SystemExit(f"macOS build output is missing: {APP_EXECUTABLE}")

    with tempfile.TemporaryDirectory(prefix="honsen_oda_dmg_") as mount_dir:
        mount = Path(mount_dir)
        attached = False
        try:
            run("hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", str(mount), str(dmg))
            attached = True
            source_app = mount / "ODAFileConverter.app"
            source_executable = source_app / ODA_EXECUTABLE
            if not source_executable.is_file():
                raise SystemExit(f"ODAFileConverter.app is missing from DMG: {dmg}")
            run("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(source_app))
            run("spctl", "--assess", "--type", "execute", "--verbose=2", str(source_app))

            app_arches = architectures(APP_EXECUTABLE)
            oda_arches = architectures(source_executable)
            if not app_arches.issubset(oda_arches):
                raise SystemExit(
                    f"Architecture mismatch: app={sorted(app_arches)}, ODA={sorted(oda_arches)}. "
                    "Use the DMG matching the Python/PyInstaller build host."
                )
        finally:
            if attached:
                run("hdiutil", "detach", str(mount))

    if ODA_DMG_RESOURCE.exists():
        raise SystemExit(f"Refusing to overwrite unexpected existing ODA resource: {ODA_DMG_RESOURCE}")
    run("ditto", str(dmg), str(ODA_DMG_RESOURCE))
    sign_command = ["codesign", "--force", "--sign", args.identity]
    if args.identity != "-":
        sign_command.extend(["--options", "runtime", "--timestamp"])
    sign_command.append(str(OUTPUT_APP))
    run(*sign_command)
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(OUTPUT_APP))

    if args.dmg_output and not args.dmg:
        raise SystemExit("--dmg-output requires --dmg")
    if args.dmg:
        dmg_output = (args.dmg_output or ROOT / "dist" / f"Honsen_CAD_Translator_v{VERSION}_macOS_{next(iter(app_arches))}.dmg")
        dmg_output = dmg_output.expanduser().resolve()
        if dmg_output.suffix.lower() != ".dmg":
            raise SystemExit(f"DMG output must end in .dmg: {dmg_output}")
        dmg_output.parent.mkdir(parents=True, exist_ok=True)
        run(
            "hdiutil", "create", "-volname", "Honsen CAD Translator", "-srcfolder", str(OUTPUT_APP),
            "-ov", "-format", "UDZO", str(dmg_output),
        )
        print(f"DMG: {dmg_output}")

    print(f"Built: {OUTPUT_APP}")
    print(f"App architectures: {', '.join(sorted(architectures(APP_EXECUTABLE)))}")
    print(f"ODA architectures: {', '.join(sorted(oda_arches))}")


if __name__ == "__main__":
    main()
