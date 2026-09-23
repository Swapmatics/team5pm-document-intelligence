"""Scan bytes before any parser opens them. A flagged file is not read."""

import os
import shutil
import subprocess
import tempfile


def scanner():
    found = shutil.which("clamscan")
    if found:
        return found
    fallback = "/opt/homebrew/bin/clamscan"
    if os.path.isfile(fallback):
        return fallback
    return ""


def scan_bytes(data):
    binary = scanner()
    if not binary:
        return "The malware scan is not available, so I did not open the file."
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        handle.write(data)
        handle.close()
        done = subprocess.run(
            [binary, "--no-summary", handle.name],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "The malware scan did not finish, so I did not open the file."
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
    if done.returncode == 0:
        return ""
    if done.returncode == 1:
        return "The malware scan flagged this file, so I did not open it."
    return "The malware scan did not finish, so I did not open the file."
