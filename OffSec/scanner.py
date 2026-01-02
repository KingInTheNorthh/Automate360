#!/usr/bin/env python3

import socket
import ssl
import sys
import json
from datetime import datetime
from typing import Optional


def resolve_target(target):
    try:
        ip = socket.gethostbyname(target)
        return ip
    except socket.gaierror:
        return None


def check_port(ip, port, timeout=1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((ip, port))
        return result == 0
    finally:
        sock.close()


def get_http_headers(host, port):
    try:
        sock = socket.create_connection((host, port), timeout=2)
        request = f"HEAD / HTTP/1.1\r\nHost: {host}\r\n\r\n"
        sock.send(request.encode())

        response = sock.recv(1024).decode(errors="ignore")
        sock.close()

        headers = {}
        for line in response.split("\r\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
        return headers

    except Exception:
        return {}


def get_tls_expiry(host: str) -> Optional[datetime]:
    try:
        context = ssl.create_default_context()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)

        wrapped_sock = context.wrap_socket(sock, server_hostname=host)
        wrapped_sock.connect((host, 443))

        cert = wrapped_sock.getpeercert()
        wrapped_sock.close()

        if not cert:
            return None

        expiry = cert.get("notAfter")
        if not isinstance(expiry, str):
            return None

        return datetime.strptime(expiry, "%b %d %H:%M:%S %Y %Z")

    except Exception:
        return None


COMMON_PORTS = {
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    443: "HTTPS",
    3306: "MySQL",
    6379: "Redis",
    8080: "HTTP-ALT",
}


def scan(target):
    ip = resolve_target(target)
    if not ip:
        print("Could not resolve target")
        sys.exit(1)

    results = {
        "target": target,
        "ip": ip,
        "open_ports": [],
        "http_headers": {},
        "tls_expiry": None,
    }

    for port, name in COMMON_PORTS.items():
        if check_port(ip, port):
            results["open_ports"].append({"port": port, "service": name})

    if any(p["port"] == 80 for p in results["open_ports"]):
        results["http_headers"] = get_http_headers(target, 80)

    if any(p["port"] == 443 for p in results["open_ports"]):
        expiry = get_tls_expiry(target)
        if expiry:
            results["tls_expiry"] = expiry.isoformat()

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sec_check.py <domain|ip> [--json]")
        sys.exit(1)

    target = sys.argv[1]
    json_mode = "--json" in sys.argv

    report = scan(target)

    if json_mode:
        print(json.dumps(report, indent=2))
    else:
        print(f"\nTarget: {report['target']} ({report['ip']})\n")

        print("Open ports:")
        for p in report["open_ports"]:
            print(f"  - {p['port']} ({p['service']})")

        if report["http_headers"]:
            print("\nHTTP headers:")
            for k, v in report["http_headers"].items():
                print(f"  {k}: {v}")

        if report["tls_expiry"]:
            print(f"\nTLS expires: {report['tls_expiry']}")
