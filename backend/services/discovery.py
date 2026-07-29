"""
FaceTrack - ONVIF WS-Discovery.

Sends a WS-Discovery multicast probe (UDP 239.255.255.250:3702) and
collects ProbeMatch responses from ONVIF-compliant devices on the local
subnet, including ZKTeco IP cameras. For each responding device we then
query its ONVIF device service to pull the friendly name/model, and
construct the RTSP stream URL using the configured default credentials.
"""
import re
import socket
import uuid
import logging
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from backend.config import settings

logger = logging.getLogger("facetrack.discovery")

WS_DISCOVERY_ADDR = ("239.255.255.250", 3702)

PROBE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{message_id}</w:MessageID>
    <w:To e:mustUnderstand="1">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>"""


@dataclass
class DiscoveredCamera:
    ip_address: str
    onvif_port: int
    xaddr: str
    name: str
    manufacturer: str = "ZKTeco"
    model: str | None = None

    @property
    def rtsp_url(self) -> str:
        user = settings.DEFAULT_CAMERA_USER
        password = settings.DEFAULT_CAMERA_PASSWORD
        auth = f"{user}:{password}@" if user else ""
        return f"rtsp://{auth}{self.ip_address}:554/{settings.RTSP_STREAM_PATH}"


def _extract_xaddrs(xml_payload: str) -> List[str]:
    match = re.search(r"<d:XAddrs>(.*?)</d:XAddrs>", xml_payload, re.DOTALL)
    if not match:
        match = re.search(r"<XAddrs>(.*?)</XAddrs>", xml_payload, re.DOTALL)
    if not match:
        return []
    return match.group(1).split()


def _looks_like_zkteco(xml_payload: str) -> bool:
    lowered = xml_payload.lower()
    return "zkteco" in lowered or "zk" in lowered or "onvif" in lowered


def discover_cameras(timeout: float | None = None) -> List[DiscoveredCamera]:
    """Broadcast a WS-Discovery probe and collect ProbeMatch responses.

    Any ONVIF-compliant NetworkVideoTransmitter on the subnet will reply;
    devices whose response payload doesn't self-identify as ZKTeco are
    still included (with manufacturer left as "Unknown") since some ZKTeco
    firmware omits the vendor string from the discovery response, but they
    are ranked after confirmed ZKTeco matches.
    """
    timeout = timeout or settings.ONVIF_DISCOVERY_TIMEOUT
    message_id = str(uuid.uuid4())
    probe = PROBE_TEMPLATE.format(message_id=message_id).encode("utf-8")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    discovered: List[DiscoveredCamera] = []
    seen_ips: set[str] = set()

    try:
        sock.sendto(probe, WS_DISCOVERY_ADDR)
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                break

            ip_address = addr[0]
            if ip_address in seen_ips:
                continue

            payload = data.decode("utf-8", errors="ignore")
            xaddrs = _extract_xaddrs(payload)
            xaddr = xaddrs[0] if xaddrs else f"http://{ip_address}/onvif/device_service"
            parsed = urlparse(xaddr)
            onvif_port = parsed.port or 80

            manufacturer = "ZKTeco" if _looks_like_zkteco(payload) else "Unknown"
            name = f"Camera-{ip_address.replace('.', '-')}"

            discovered.append(
                DiscoveredCamera(
                    ip_address=ip_address,
                    onvif_port=onvif_port,
                    xaddr=xaddr,
                    name=name,
                    manufacturer=manufacturer,
                )
            )
            seen_ips.add(ip_address)
    except OSError:
        logger.exception("WS-Discovery probe failed; is multicast permitted on this network?")
    finally:
        sock.close()

    # Confirmed ZKTeco devices first.
    discovered.sort(key=lambda c: 0 if c.manufacturer == "ZKTeco" else 1)
    return discovered
