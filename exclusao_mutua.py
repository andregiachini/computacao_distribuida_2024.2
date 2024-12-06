import socket
import threading
import time
import sys

class DistributedMutexProcess:
    def __init__(self, process_id, port, peers):
        self.process_id = process_id
        self.port = port
        self.peers = peers
        self.request_queue = []
        self.in_critical_section = False
        self.ok_count = 0
        self.lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("localhost", self.port))
    
    def send_message(self, message, peer):
        self.sock.sendto(message.encode(), peer)
        print(f"[Process {self.process_id}] Sent message: {message} to {peer}")

    def handle_request(self, requester_id, requester_port):
        with self.lock:
            if self.in_critical_section or self.request_queue:
                self.request_queue.append((requester_id, requester_port))
                print(f"[Process {self.process_id}] Request from {requester_id} added to queue.")
            else:
                time.sleep(0.5)
                self.send_message("OK", ("localhost", requester_port))
                print(f"[Process {self.process_id}] Sent OK to {requester_id}.")

    def enter_critical_section(self):
        with self.lock:
            self.in_critical_section = True
            print(f"[Process {self.process_id}] Entering critical section.")
    
    def exit_critical_section(self):
        with self.lock:
            self.in_critical_section = False
            print(f"[Process {self.process_id}] Exiting critical section.")
            while self.request_queue:
                requester_id, requester_port = self.request_queue.pop(0)
                time.sleep(0.5)
                self.send_message("OK", ("localhost", requester_port))
                print(f"[Process {self.process_id}] Sent OK to {requester_id} from queue.")
        for peer_host, peer_port in self.peers:
            self.send_message(f"RELEASE {self.process_id}", (peer_host, peer_port))
            print(f"[Process {self.process_id}] Sent RELEASE to {peer_host}:{peer_port}.")
            time.sleep(0.5)
    
    def request_critical_section(self):
        print(f"[Process {self.process_id}] Requesting critical section.")
        self.ok_count = 0
        for peer_host, peer_port in self.peers:
            self.send_message(f"REQUEST {self.process_id} {self.port}", (peer_host, peer_port))
            print(f"[Process {self.process_id}] Sent request to {peer_host}:{peer_port}")
            time.sleep(0.5)
        
        print(f"[Process {self.process_id}] Waiting for OKs from peers...")
        while True:
            with self.lock:
                if self.ok_count >= len(self.peers):
                    break
            time.sleep(0.1)
        
        self.enter_critical_section()

    def listener(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            message = data.decode()
            print(f"[Process {self.process_id}] Listener received message: {message} from {addr}")
            parts = message.split()
            if parts[0] == "REQUEST":
                requester_id = int(parts[1])
                requester_port = int(parts[2])
                self.handle_request(requester_id, requester_port)
            elif parts[0] == "RELEASE":
                with self.lock:
                    if self.request_queue:
                        requester_id, requester_port = self.request_queue.pop(0)
                        time.sleep(0.5)
                        self.send_message("OK", ("localhost", requester_port))
                        print(f"[Process {self.process_id}] Sent OK to {requester_id} from queue.")
            elif message == "OK":
                with self.lock:
                    self.ok_count += 1

    def run(self):
        threading.Thread(target=self.listener, daemon=True).start()
        while True:
            command = input(f"[Process {self.process_id}] Enter 'request' to request critical section or 'exit' to quit: ").strip()
            if command.lower() == "request":
                self.request_critical_section()
                time.sleep(3)
                self.exit_critical_section()
            elif command.lower() == "exit":
                print(f"[Process {self.process_id}] Exiting.")
                break

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process.py <process_id> <port> <peer1_host>:<peer1_port> ...")
        sys.exit(1)

    process_id = int(sys.argv[1])
    port = int(sys.argv[2])
    peers = []
    for peer in sys.argv[3:]:
        host, peer_port = peer.split(":")
        peers.append((host, int(peer_port)))
    
    process = DistributedMutexProcess(process_id, port, peers)
    process.run()