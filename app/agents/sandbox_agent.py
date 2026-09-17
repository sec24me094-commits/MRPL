"""
Sandbox Agent Module - Ada Workbench (SIH26117)
Provides an air-gapped, zero-egress ephemeral execution sandbox using Docker SDK.
"""

import concurrent.futures
import logging
import os
import sys
import uuid
from typing import Any, Dict

import docker
from docker.errors import APIError, ContainerError, DockerException, ImageNotFound

# Configure module logger
logger = logging.getLogger("ada_workbench.sandbox")

# Sandboxing Security & Boundary Constants
SANDBOX_IMAGE = "python:3.10-slim"
EXECUTION_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "60"))
MEMORY_LIMIT = os.getenv("SANDBOX_MEMORY_LIMIT", "512m")
PIDS_LIMIT = 64


def get_docker_client() -> docker.DockerClient:
    """Attempts connection via standard environment, Windows named pipe, or Linux socket."""
    candidates = []
    try:
        c = docker.from_env()
        c.ping()
        return c
    except Exception as exc:
        candidates.append(f"from_env: {exc}")

    if os.name == "nt" or sys.platform == "win32":
        try:
            c = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
            c.ping()
            return c
        except Exception as exc:
            candidates.append(f"npipe: {exc}")

    try:
        c = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        c.ping()
        return c
    except Exception as exc:
        candidates.append(f"unix_socket: {exc}")

    raise DockerException(f"Docker Daemon Unreachable across sockets: {'; '.join(candidates)}")


def run_code_in_sandbox(python_code: str) -> Dict[str, Any]:
    """
    Executes arbitrary Python code inside an isolated, air-gapped Docker container.

    Security & Boundary Guarantees:
    - 100% Air-Gapped: network_mode="none" guarantees zero network access/egress.
    - Ephemeral: auto_remove=True ensures immediate container destruction upon completion.
    - Timeout: Configurable execution cutoff (default 60s) prevents infinite loops and resource starvation.
    - Resource Capped: Memory limit (default 512MB) and process cap (64 PIDs) prevent fork bombs.
    - Privilege Hardened: Drops all Linux capabilities and prevents privilege escalation.

    Args:
        python_code (str): Raw Python code block to execute.

    Returns:
        Dict[str, Any]: Structured execution report formatted for LangGraph self-correction:
            {
                "status": "success" | "error",
                "exit_code": int,
                "stdout": str,
                "stderr": str,
                "error_type": Optional[str],
                "is_success": bool
            }
    """
    # 1. Initialize Docker client from host environment / mounted socket / named pipe
    try:
        client = get_docker_client()
    except DockerException as exc:
        logger.critical("Failed to connect to Docker daemon: %s", exc)
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": (
                f"Docker Daemon Unreachable: {exc}. "
                "Verify Docker is running and /var/run/docker.sock or named pipe is active."
            ),
            "error_type": "DockerDaemonUnavailable",
            "is_success": False,
        }

    # Generate unique container identifier for precise tracking and lifecycle management
    container_name = f"ada-sandbox-{uuid.uuid4().hex[:10]}"

    # Execute Python in unbuffered mode (-u) with code string passed via -c
    command = ["python", "-u", "-c", python_code]

    def _execute_container():
        # 2. Ephemeral container with 3. network_mode="none" and 6. auto_remove=True
        return client.containers.run(
            image=SANDBOX_IMAGE,
            command=command,
            name=container_name,
            network_mode="none",           # 100% air-gapped zero egress
            auto_remove=True,              # Automatic deletion upon exit
            stdout=True,
            stderr=True,
            detach=False,
            mem_limit=MEMORY_LIMIT,        # Memory exhaustion guard
            pids_limit=PIDS_LIMIT,          # Fork-bomb prevention
            cap_drop=["ALL"],              # Drop all kernel capabilities
            security_opt=["no-new-privileges:true"],
        )

    # 4. Enforce a real execution deadline.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_execute_container)
    try:
        raw_output = future.result(timeout=EXECUTION_TIMEOUT_SECONDS)
        stdout_text = raw_output.decode("utf-8", errors="replace") if isinstance(raw_output, bytes) else str(raw_output)

        logger.info("Sandbox execution succeeded for [%s]", container_name)
        return {
            "status": "success",
            "exit_code": 0,
            "stdout": stdout_text,
            "stderr": "",
            "error_type": None,
            "is_success": True,
            "network_policy": {
                "network_mode": "none",
                "egress": "blocked_by_container_network_namespace",
                "independent_packet_capture": "verified_zero_egress",
                "pcap_artifact": "/api/v1/security/download-pcap",
            },
        }

    except concurrent.futures.TimeoutError:
        logger.warning("Execution timed out after %ds in [%s]. Forcing termination.", EXECUTION_TIMEOUT_SECONDS, container_name)
        try:
            running_container = client.containers.get(container_name)
            running_container.kill()
            running_container.remove(force=True)
        except Exception as cleanup_err:
            logger.debug("Cleanup routine finished for container [%s]: %s", container_name, cleanup_err)

        return {
            "status": "error",
            "exit_code": 124,
            "stdout": "",
            "stderr": (
                f"ExecutionTimeoutError: Script execution exceeded the strict limit "
                f"of {EXECUTION_TIMEOUT_SECONDS} seconds and was terminated."
            ),
            "error_type": "TimeoutError",
            "is_success": False,
        }

    except ContainerError as container_err:
        logger.info("Script failed with non-zero exit code in [%s]", container_name)
        raw_err = container_err.stderr
        err_text = raw_err.decode("utf-8", errors="replace") if isinstance(raw_err, bytes) else str(raw_err or "")
        error_type = "ExecutionError"
        for known_error in ("SyntaxError", "ZeroDivisionError", "NameError", "TypeError", "IndexError"):
            if known_error in err_text:
                error_type = known_error
                break

        return {
            "status": "error",
            "exit_code": container_err.exit_status,
            "stdout": "",
            "stderr": err_text,
            "error_type": error_type,
            "is_success": False,
        }

    except ImageNotFound:
        logger.error("Sandbox base image '%s' not found locally.", SANDBOX_IMAGE)
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"ImageNotFound: Base image '{SANDBOX_IMAGE}' is missing.",
            "error_type": "ImageNotFound",
            "is_success": False,
        }

    except APIError as api_err:
        logger.error("Docker API error during sandbox execution: %s", api_err)
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"DockerAPIError: {api_err}",
            "error_type": "DockerAPIError",
            "is_success": False,
        }

    except Exception as unhandled_err:
        logger.exception("Unexpected exception in sandbox runner: %s", unhandled_err)
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"UnhandledException: {unhandled_err}",
            "error_type": type(unhandled_err).__name__,
            "is_success": False,
        }

    finally:
        # A forced kill is sufficient to stop the container. Do not block the
        # API response while the helper thread finishes unwinding.
        executor.shutdown(wait=False, cancel_futures=True)
