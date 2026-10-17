"""check_docker.py - `make docker-check`, without a shell.

The old version was:

    @command -v $(DOCKER) >/dev/null 2>&1 || { echo "docker not found on PATH."; ...; }

Two problems:

* `command -v` is a POSIX shell builtin. It is not available on a stock Windows
  shell, so the check either errored out or was skipped depending on the machine -
  i.e. it did not reliably do the thing it exists to do.
* It only checked that the docker BINARY exists. With Docker Desktop installed but
  not running, the binary is present and `docker --version` succeeds, so the check
  passed and then `make run` failed with a named-pipe error pointing at nothing a
  judge could act on.

This checks the daemon too, and says which of the two things is missing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    docker = "docker"

    if not shutil.which(docker):
        print()
        print("  docker was not found on PATH.")
        print()
        print("  Install Docker Desktop, or run the suite without Docker:")
        print()
        print("      make verify    offline verification, no Docker, no model")
        print("      make test      every automated check")
        print()
        return 1

    rc, out = run([docker, "--version"])
    if rc != 0:
        print(f"  docker is on PATH but did not run: {out[:300]}")
        return 1
    print(f"  {out}")

    # The daemon, not just the binary.
    rc, out = run([docker, "info", "--format", "{{.ServerVersion}}"])
    if rc != 0:
        print()
        print("  The Docker CLI works but the DAEMON is not reachable.")
        print()
        print("  With Docker Desktop, start it and wait for the whale to settle,")
        print("  then re-run. Typical cause of this message:")
        print()
        for line in out.splitlines()[:4]:
            print(f"      {line}")
        print()
        print("  If you are not using Docker Desktop, start the service your")
        print("  platform provides. `make verify` needs no daemon at all.")
        print()
        return 1

    print(f"  daemon {out} reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())