import argparse
import socket
import sys
import time

from utils import ACK, DATA, END, MAX_PAYLOAD_SIZE, START, make_packet, parse_packet


RETRANSMIT_TIMEOUT = 0.5
POLL_INTERVAL = 0.05


def chunk_message(message):
    return [message[i : i + MAX_PAYLOAD_SIZE] for i in range(0, len(message), MAX_PAYLOAD_SIZE)]


def receive_ack(sock, timeout=None):
    previous_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        packet_bytes, _ = sock.recvfrom(2048)
    except socket.timeout:
        return None
    finally:
        sock.settimeout(previous_timeout)

    parsed_packet = parse_packet(packet_bytes)
    if parsed_packet is None:
        return None

    header, _ = parsed_packet
    if header.type != ACK:
        return None
    return header


def sender(receiver_ip, receiver_port, window_size):
    destination = (receiver_ip, receiver_port)
    message = sys.stdin.buffer.read()
    data_chunks = chunk_message(message)
    data_packets = {
        seq_num: make_packet(DATA, seq_num, chunk)
        for seq_num, chunk in enumerate(data_chunks, start=1)
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.sendto(make_packet(START, 0), destination)
    while True:
        ack_header = receive_ack(sock, POLL_INTERVAL)
        if ack_header is not None and ack_header.seq_num == 1:
            break

    total_packets = len(data_chunks)
    base_seq = 1
    next_seq = 1
    acknowledged = set()
    timer_started_at = None

    while base_seq <= total_packets:
        while next_seq <= total_packets and next_seq < base_seq + window_size:
            sock.sendto(data_packets[next_seq], destination)
            next_seq += 1

        if base_seq < next_seq and timer_started_at is None:
            timer_started_at = time.monotonic()

        ack_header = receive_ack(sock, POLL_INTERVAL)
        if ack_header is not None and base_seq <= ack_header.seq_num < next_seq:
            acknowledged.add(ack_header.seq_num)

            old_base = base_seq
            while base_seq in acknowledged:
                base_seq += 1

            if base_seq != old_base:
                timer_started_at = time.monotonic() if base_seq < next_seq else None

        if (
            base_seq <= total_packets
            and timer_started_at is not None
            and time.monotonic() - timer_started_at >= RETRANSMIT_TIMEOUT
        ):
            for seq_num in range(base_seq, next_seq):
                if seq_num not in acknowledged:
                    sock.sendto(data_packets[seq_num], destination)
            timer_started_at = time.monotonic()

    end_seq = total_packets + 1
    sock.sendto(make_packet(END, end_seq), destination)
    end_deadline = time.monotonic() + RETRANSMIT_TIMEOUT
    while True:
        remaining = end_deadline - time.monotonic()
        if remaining <= 0:
            break

        ack_header = receive_ack(sock, min(POLL_INTERVAL, remaining))
        if ack_header is not None and ack_header.seq_num == end_seq + 1:
            break

    sock.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
