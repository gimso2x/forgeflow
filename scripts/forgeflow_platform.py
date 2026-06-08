#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

UTF8_TEXT = {"text": True, "encoding": "utf-8", "errors": "replace"}


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def run_utf8(args: Sequence[str], *, cwd: Path | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **UTF8_TEXT,
        **kwargs,
    )


def run_shell_utf8(command: str, *, cwd: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        check=False,
        **UTF8_TEXT,
    )


def safe_rmtree(path: Path | str) -> None:
    target = Path(path)

    def retry_remove(function: object, failed_path: str, _exc: BaseException) -> None:
        failed = Path(failed_path)
        try:
            os.chmod(failed, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        except OSError:
            pass
        for _attempt in range(3):
            try:
                function(failed_path)
                return
            except OSError:
                time.sleep(0.05)
        function(failed_path)

    try:
        shutil.rmtree(target, onexc=retry_remove)
    except TypeError:
        shutil.rmtree(target, onerror=lambda function, failed_path, exc_info: retry_remove(function, failed_path, exc_info[1]))
