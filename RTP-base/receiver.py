import argparse
import socket
import sys

from utils import ACK, DATA, END, START, make_packet, parse_packet


def send_ack(sock, address, seq_num):
    sock.sendto(make_packet(ACK, seq_num), address)


def receiver(receiver_ip, receiver_port, window_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((receiver_ip, receiver_port))

    stdout = sys.stdout.buffer
    active_sender = None
    expected_seq = 1
    buffered_packets = {}

    while True:
        packet_bytes, address = sock.recvfrom(2048)
        parsed_packet = parse_packet(packet_bytes)
        if parsed_packet is None:
            continue

        header, payload = parsed_packet

        if active_sender is not None and address != active_sender:
            continue

        if header.type == START:
            if active_sender is None:
                active_sender = address
                expected_seq = 1
                buffered_packets = {}
                send_ack(sock, active_sender, 1)
            continue

        if active_sender is None:
            continue

        if header.type == DATA:
            seq_num = header.seq_num

            if seq_num >= expected_seq + window_size:
                send_ack(sock, active_sender, expected_seq)
                continue

            if seq_num >= expected_seq and seq_num not in buffered_packets:
                buffered_packets[seq_num] = payload

            if seq_num == expected_seq:
                while expected_seq in buffered_packets:
                    stdout.write(buffered_packets.pop(expected_seq))
                    expected_seq += 1
                stdout.flush()

            send_ack(sock, active_sender, expected_seq)
            continue

        if header.type == END:
            if header.seq_num == expected_seq:
                send_ack(sock, active_sender, header.seq_num + 1)
                stdout.flush()
                sock.close()
                return

            send_ack(sock, active_sender, expected_seq)


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

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
