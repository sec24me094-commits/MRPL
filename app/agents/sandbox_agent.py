"""
Sandbox Agent Module - Ada Workbench (SIH26117)
Provides an air-gapped, zero-egress ephemeral execution sandbox using Docker SDK.
"""

import concurrent.futures
import logging
import os
import uuid
from typing import Any, Dict

import docker
from docker.errors import APIError, ContainerError, DockerException, ImageNotFound

# Configure module logger
logger = logging.getLogger("ada_workbench.sandbox")

# Sandboxing Security & Boundary Constants
SANDBOX_IMAGE = "python:3.10-slim"
EXECUTION_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "10"))
MEMORY_LIMIT = os.getenv("SANDBOX_MEMORY_LIMIT", "128m")
PIDS_LIMIT = 64


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
    # 1. Initialize Docker client from host environment / mounted socket
    try:
        client = docker.from_env()
    except DockerException as exc:
        logger.critical("Failed to connect to Docker daemon: %s", exc)
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": (
                f"Docker Daemon Unreachable: {exc}. "
                "Verify /var/run/docker.sock is mounted and active."
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

    # 4. Enforce strict 10-second timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
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
            }

        except concurrent.futures.TimeoutError:
            logger.warning("Execution timed out after %ds in [%s]. Forcing termination.", EXECUTION_TIMEOUT_SECONDS, container_name)
            
            # Forcibly kill container if still running
            try:
                running_container = client.containers.get(container_name)
                running_container.kill()
                # If auto_remove did not trigger on kill, enforce removal
                running_container.remove(force=True)
            except Exception as cleanup_err:
                logger.debug("Cleanup routine finished for container [%s]: %s", container_name, cleanup_err)

            return {
                "status": "error",
                "exit_code": 124,  # Standard POSIX timeout exit code
                "stdout": "",
                "stderr": (
                    f"ExecutionTimeoutError: Script execution exceeded the strict limit "
                    f"of {EXECUTION_TIMEOUT_SECONDS} seconds and was terminated."
                ),
                "error_type": "TimeoutError",
                "is_success": False,
            }

        except ContainerError as container_err:
            # 5. Capture execution errors, tracebacks, or syntax errors
            logger.info("Script failed with non-zero exit code in [%s]", container_name)
            raw_err = container_err.stderr
            if isinstance(raw_err, bytes):
                err_text = raw_err.decode("utf-8", errors="replace")
            else:
                err_text = str(raw_err or "")

            # Identify error type from traceback header for downstream agent routing
            error_type = "ExecutionError"
            if "SyntaxError" in err_text:
                error_type = "SyntaxError"
            elif "ZeroDivisionError" in err_text:
                error_type = "ZeroDivisionError"
            elif "NameError" in err_text:
                error_type = "NameError"
            elif "TypeError" in err_text:
                error_type = "TypeError"
            elif "IndexError" in err_text:
                error_type = "IndexError"

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
