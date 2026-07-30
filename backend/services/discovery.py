"""
FaceTrack - ONVIF WS-Discovery with subnet scanning support.
"""
import re
import socket
import uuid
import logging
import ipaddress
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse
import requests
from requests.auth import HTTPDigestAuth

from config import settings

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
    rtsp_port: int = 554

    @property
    def rtsp_url(self) -> str:
        user = settings.DEFAULT_CAMERA_USER
        password = settings.DEFAULT_CAMERA_PASSWORD
        auth = f"{user}:{password}@" if user and password else ""
        # Try common RTSP paths for ZKTeco cameras
        rtsp_paths = [
            "/stream1",
            "/Streaming/Channels/101",
            "/cam/realmonitor?channel=1&subtype=0",
            "/live",
        ]
        # Use configured path
        path = settings.RTSP_STREAM_PATH if settings.RTSP_STREAM_PATH else rtsp_paths[0]
        if not path.startswith("/"):
            path = f"/{path}"
        return f"rtsp://{auth}{self.ip_address}:{self.rtsp_port}{path}"


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


def _get_camera_name(ip: str, port: int = 80) -> Optional[str]:
    """Try to get camera name via ONVIF device info."""
    try:
        # ONVIF GetDeviceInformation request
        body = """<?xml version="1.0" encoding="UTF-8"?>
        <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
          <s:Body>
            <GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>
          </s:Body>
        </s:Envelope>"""
        
        url = f"http://{ip}:{port}/onvif/device_service"
        auth = HTTPDigestAuth(settings.DEFAULT_CAMERA_USER, settings.DEFAULT_CAMERA_PASSWORD)
        response = requests.post(url, data=body, auth=auth, timeout=3.0)
        
        if response.status_code == 200:
            # Extract manufacturer and model
            manufacturer_match = re.search(r"<Manufacturer>(.*?)</Manufacturer>", response.text)
            model_match = re.search(r"<Model>(.*?)</Model>", response.text)
            name_match = re.search(r"<Name>(.*?)</Name>", response.text)
            
            manufacturer = manufacturer_match.group(1) if manufacturer_match else "ZKTeco"
            model = model_match.group(1) if model_match else None
            name = name_match.group(1) if name_match else f"Camera-{ip.replace('.', '-')}"
            return name, manufacturer, model
    except Exception as e:
        logger.debug(f"Could not get device info for {ip}: {e}")
    return None, "ZKTeco", None


def discover_cameras(timeout: float | None = None) -> List[DiscoveredCamera]:
    """Broadcast a WS-Discovery probe and collect ProbeMatch responses.
    Also performs direct IP scanning of the configured subnet as fallback."""
    timeout = timeout or settings.ONVIF_DISCOVERY_TIMEOUT
    message_id = str(uuid.uuid4())
    probe = PROBE_TEMPLATE.format(message_id=message_id).encode("utf-8")

    discovered: List[DiscoveredCamera] = []
    seen_ips: set[str] = set()

    # Method 1: WS-Discovery multicast
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

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

                # Try to get proper camera name
                name, manufacturer, model = _get_camera_name(ip_address, onvif_port)
                if not name:
                    name = f"Camera-{ip_address.replace('.', '-')}"
                if not manufacturer:
                    manufacturer = "ZKTeco" if _looks_like_zkteco(payload) else "Unknown"

                discovered.append(
                    DiscoveredCamera(
                        ip_address=ip_address,
                        onvif_port=onvif_port,
                        xaddr=xaddr,
                        name=name,
                        manufacturer=manufacturer,
                        model=model,
                    )
                )
                seen_ips.add(ip_address)
        except OSError:
            logger.exception("WS-Discovery probe failed; is multicast permitted on this network?")
        finally:
            sock.close()
    except Exception as e:
        logger.error(f"WS-Discovery error: {e}")

    # Method 2: Direct subnet scanning for cameras that don't respond to multicast
    try:
        subnet = settings.DISCOVERY_SUBNET
        network = ipaddress.ip_network(subnet, strict=False)
        
        # Common ONVIF ports to check
        onvif_ports = [80, 8080, 8899]
        
        logger.info(f"Scanning subnet {subnet} for ONVIF cameras...")
        
        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str in seen_ips:
                continue
                
            for port in onvif_ports:
                try:
                    # Quick socket test to see if port is open
                    sock_test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock_test.settimeout(0.5)
                    result = sock_test.connect_ex((ip_str, port))
                    sock_test.close()
                    
                    if result == 0:
                        # Try to get device info
                        name, manufacturer, model = _get_camera_name(ip_str, port)
                        if name:
                            discovered.append(
                                DiscoveredCamera(
                                    ip_address=ip_str,
                                    onvif_port=port,
                                    xaddr=f"http://{ip_str}:{port}/onvif/device_service",
                                    name=name,
                                    manufacturer=manufacturer or "ZKTeco",
                                    model=model,
                                )
                            )
                            seen_ips.add(ip_str)
                            logger.info(f"Found camera at {ip_str}:{port} - {name}")
                            break  # Found ONVIF on this IP, move to next
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Subnet scan error: {e}")

    # Sort by manufacturer (ZKTeco first) then by IP
    discovered.sort(key=lambda c: (0 if c.manufacturer == "ZKTeco" else 1, c.ip_address))
    
    logger.info(f"Discovered {len(discovered)} cameras total")
    return discovered


def scan_specific_ip(ip_address: str) -> Optional[DiscoveredCamera]:
    """Scan a specific IP address for an ONVIF camera."""
    onvif_ports = [80, 8080, 8899]
    
    for port in onvif_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            
            if result == 0:
                name, manufacturer, model = _get_camera_name(ip_address, port)
                if name:
                    return DiscoveredCamera(
                        ip_address=ip_address,
                        onvif_port=port,
                        xaddr=f"http://{ip_address}:{port}/onvif/device_service",
                        name=name,
                        manufacturer=manufacturer or "ZKTeco",
                        model=model,
                    )
        except Exception:
            continue
    return None