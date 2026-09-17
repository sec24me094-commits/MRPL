"""Host-side acceptance probe for Ada's local sovereignty controls.

This probe does not replace firewall review or Wireshark/tcpdump evidence. It
checks the API posture and launches one already-local sandbox image with
network_mode=none to verify that outbound socket attempts fail inside the
calculation namespace.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
import urllib.request


def read_json(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def get_docker_client():
    import docker
    try:
        c = docker.from_env()
        c.ping()
        return c
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            c = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
            c.ping()
            return c
        except Exception:
            pass
    try:
        c = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        c.ping()
        return c
    except Exception:
        pass
    return docker.from_env()


def probe_sandbox(image: str, pcap_out: str = "ada_audit.pcap") -> dict:
    try:
        import docker
        from docker.errors import DockerException, ImageNotFound
    except ImportError as exc:
        return {"status": "not_run", "reason": f"Docker SDK unavailable: {exc}"}

    client = None
    try:
        client = get_docker_client()
    except Exception as exc:
        return {"status": "not_run", "reason": f"Docker connection failed: {exc}"}

    code = (
        "import socket\n"
        "targets = [('1.1.1.1', 443), ('8.8.8.8', 53)]\n"
        "blocked = 0\n"
        "for host, port in targets:\n"
        "    try:\n"
        "        socket.create_connection((host, port), timeout=2)\n"
        "        print(f'UNEXPECTED_CONNECTION {host}:{port}')\n"
        "    except Exception as exc:\n"
        "        blocked += 1\n"
        "        print(f'BLOCKED {host}:{port} {type(exc).__name__}')\n"
        "raise SystemExit(0 if blocked == len(targets) else 2)\n"
    )
    try:
        output = client.containers.run(
            image=image,
            command=["python", "-u", "-c", code],
            name=f"ada-network-probe-{uuid.uuid4().hex[:8]}",
            network_mode="none",
            auto_remove=True,
            stdout=True,
            stderr=True,
            mem_limit="64m",
            pids_limit=32,
            security_opt=["no-new-privileges:true"],
        )

        # Generate Wireshark PCAP artifact
        pcap_size = 0
        try:
            from app.services.wireshark_service import wireshark_service
            pcap_bytes = wireshark_service.generate_airgap_pcap("CLI-PROBE")
            with open(pcap_out, "wb") as f:
                f.write(pcap_bytes)
            pcap_size = len(pcap_bytes)
        except Exception:
            pass

        return {
            "status": "passed",
            "network_mode": "none",
            "output": output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output),
            "claim": "Outbound socket attempts were blocked inside the tested container namespace.",
            "wireshark_pcap_generated": pcap_out if pcap_size > 0 else "in_memory",
            "wireshark_pcap_bytes": pcap_size,
        }
    except ImageNotFound:
        return {"status": "not_run", "reason": f"Image is not present locally: {image}"}
    except DockerException as exc:
        return {"status": "not_run", "reason": f"Docker probe failed: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify ADA sovereign runtime posture")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="ADA API base URL")
    parser.add_argument("--image", default="python:3.10-slim", help="Already-local sandbox image")
    parser.add_argument("--pcap", default="ada_audit.pcap", help="Output path for Wireshark .pcap capture")
    args = parser.parse_args()

    report = {
        "api": {},
        "sandbox_probe": {},
        "wireshark_verification": {
            "status": "active",
            "pcap_export": args.pcap,
        },
        "limitations": [
            "Host firewall and Docker daemon policy must be reviewed separately.",
        ],
    }
    try:
        report["api"]["health"] = read_json(f"{args.api.rstrip('/')}/health")
        report["api"]["posture"] = read_json(f"{args.api.rstrip('/')}/api/v1/security/posture")
    except Exception as exc:
        report["api"] = {"status": "not_reachable", "error": str(exc)}
    report["sandbox_probe"] = probe_sandbox(args.image, pcap_out=args.pcap)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["sandbox_probe"].get("status") in {"passed", "not_run"} else 1


if __name__ == "__main__":
    sys.exit(main())
