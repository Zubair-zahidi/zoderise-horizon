from __future__ import annotations

import io
import ipaddress
import socket
from urllib.parse import urlparse


def local_ipv4_addresses() -> list[str]:
    """Return useful private LAN addresses without contacting an external service."""
    found: set[str] = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            ip = ipaddress.ip_address(address)
            if ip.version == 4 and ip.is_private and not ip.is_loopback and not ip.is_link_local:
                found.add(address)
    except OSError:
        pass
    # getaddrinfo can return only loopback on some Windows configurations.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))  # TEST-NET; UDP connect sends no packet.
            address = probe.getsockname()[0]
            if ipaddress.ip_address(address).is_private:
                found.add(address)
    except OSError:
        pass
    return sorted(found, key=lambda value: tuple(int(part) for part in value.split(".")))


def hub_urls(port: int) -> list[str]:
    return [f"http://{address}:{port}" for address in local_ipv4_addresses()]


def normalize_hub_url(value: str) -> str:
    """Accept HTTPS anywhere and HTTP only for loopback/private network hosts."""
    raw = (value or "").strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Enter a complete http:// or https:// Zoderise Hub address.")
    # Accessing port validates malformed and out-of-range values in urllib.
    if parsed.port is not None and parsed.port < 1:
        raise ValueError("Hub ports must be between 1 and 65535.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Enter only the Hub address, without a page, query, or fragment.")
    if parsed.scheme == "http":
        host = parsed.hostname.lower()
        allowed = host in {"localhost", "localhost.localdomain"}
        if not allowed:
            try:
                ip = ipaddress.ip_address(host)
                allowed = ip.is_private or ip.is_loopback
            except ValueError:
                allowed = host.endswith(".local")
        if not allowed:
            raise ValueError("Public Hub addresses must use HTTPS. HTTP is allowed only on a private LAN.")
    return raw


def qr_png(data: str) -> bytes | None:
    """Create a QR image when the optional qrcode package is installed."""
    try:
        import qrcode
        code = qrcode.QRCode(version=None, box_size=8, border=3)
        code.add_data(data)
        code.make(fit=True)
        image = code.make_image(fill_color="#0b1020", back_color="#fffaf0")
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
    except Exception:
        return None
