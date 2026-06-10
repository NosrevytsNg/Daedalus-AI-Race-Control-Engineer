import socket

UDP_IP = "0.0.0.0"
UDP_PORT = 20777


def start_listener():
    print("Daedalus Telemetry Core Started")
    print(f"Listening on UDP Port {UDP_PORT}...")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        data, address = sock.recvfrom(4096)

        print(
            f"Packet received from {address[0]}:{address[1]}"
        )
        print(
            f"Packet size: {len(data)} bytes"
        )
        print("-" * 40)