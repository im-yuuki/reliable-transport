import binascii
import struct


START = 0
END = 1
DATA = 2
ACK = 3

HEADER_SIZE = 16
MAX_PACKET_SIZE = 1472
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - HEADER_SIZE


class PacketHeader:
    def __init__(self, type=0, seq_num=0, length=0, checksum=0):
        self.type = type
        self.seq_num = seq_num
        self.length = length
        self.checksum = checksum

    def __bytes__(self):
        return struct.pack("!iiiI", self.type, self.seq_num, self.length, self.checksum)

    @classmethod
    def from_bytes(cls, packet_bytes):
        type, seq_num, length, checksum = struct.unpack("!iiiI", packet_bytes)
        return cls(type=type, seq_num=seq_num, length=length, checksum=checksum)


def compute_checksum(pkt):
    return binascii.crc32(bytes(pkt)) & 0xFFFFFFFF


def make_packet(packet_type, seq_num, payload=b""):
    header = PacketHeader(type=packet_type, seq_num=seq_num, length=len(payload), checksum=0)
    header.checksum = compute_checksum(bytes(header) + payload)
    return bytes(header) + payload


def parse_packet(packet_bytes):
    if len(packet_bytes) < HEADER_SIZE:
        return None

    header = PacketHeader.from_bytes(packet_bytes[:HEADER_SIZE])
    total_length = HEADER_SIZE + header.length
    if header.length < 0 or len(packet_bytes) != total_length:
        return None

    payload = packet_bytes[HEADER_SIZE:total_length]
    packet_checksum = header.checksum
    header.checksum = 0
    if compute_checksum(bytes(header) + payload) != packet_checksum:
        return None

    header.checksum = packet_checksum
    return header, payload
