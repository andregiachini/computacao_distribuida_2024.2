import socket
import threading
import pickle
from multiprocessing import Process
import time

NODES = {
    "N1": {"host": "localhost", "port": 5006, "start": 1, "end": 10},
    "N2": {"host": "localhost", "port": 5005, "start": 11, "end": 20},
}

def hash_function(card_number, security_code, expiry_date):
    combined = f"{card_number}{security_code}{expiry_date}"
    return (sum(ord(char) for char in combined) % 20) + 1

def handle_request(conn, addr, node_name, storage, start, end):
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            request = pickle.loads(data)
            operation = request['operation']
            card_number = request.get('card_number')
            security_code = request.get('security_code')
            expiry_date = request.get('expiry_date')

            if operation == 'store':
                store(card_number, security_code, expiry_date, node_name, storage, start, end)
            elif operation == 'retrieve':
                retrieve(card_number, security_code, expiry_date, node_name, storage, start, end)
            elif operation == 'print_storage':
                print_storage(node_name, storage)
        except Exception as e:
            print(f"[{node_name}] Erro: {e}")
            break
    conn.close()

def store(card_number, security_code, expiry_date, node_name, storage, start, end):
    address = hash_function(card_number, security_code, expiry_date)
    print(f"[{node_name}] Calculado endereço {address} para armazenar os dados.")
    index = address - start
    if start <= address <= end:
        if 0 <= index < len(storage):
            if storage[index] is None:
                storage[index] = (card_number, security_code, expiry_date)
                print(f"[{node_name}] Dados armazenados na posição {address}.")
            else:
                print(f"[{node_name}] Colisão na posição {address}. Tentando próxima posição...")
                for i in range(index + 1, index + 1 + len(storage)):
                    circular_index = i % len(storage)
                    if storage[circular_index] is None:
                        storage[circular_index] = (card_number, security_code, expiry_date)
                        print(f"[{node_name}] Dados armazenados na posição {start + circular_index}.")
                        return
                print(f"[{node_name}] Erro: Não há espaço disponível para armazenar os dados.")
        else:
            print(f"[{node_name}] Erro: Índice {index} fora do intervalo.")
    else:
        forward_request(card_number, security_code, expiry_date, 'store', node_name)

def store_stealth(card_number, security_code, expiry_date, node_name, storage, start, end):
    address = hash_function(card_number, security_code, expiry_date)
    print(f"[{node_name}] Calculado endereço {address} para armazenar os dados.")
    index = address - start
    if start <= address <= end:
        if 0 <= index < len(storage):
            if storage[index] is None:
                storage[index] = (card_number, security_code, expiry_date)
                print(f"[{node_name}] Seu cartão não foi vazado. Pode ficar tranquilo.")
            else:
                print(f"[{node_name}] Ainda não encontramos vazamento do seu cartão na primeira base de dados, vamos fazer uma varredura maior.")
                for i in range(index + 1, index + 1 + len(storage)):
                    circular_index = i % len(storage)
                    if storage[circular_index] is None:
                        storage[circular_index] = (card_number, security_code, expiry_date)
                        print(f"[{node_name}] Seu cartão não foi vazado. Pode ficar tranquilo.")
                        return
                print(f"[{node_name}] Erro: Tivemos um problema com a busca do seu cartão. Tente novamente mais tarde.")
        else:
            print(f"[{node_name}] Erro: Índice {index} fora do intervalo. Nossa base de dados está com problemas. Tente novamente mais tarde.")
    else:
        forward_request(card_number, security_code, expiry_date, 'store', node_name)

def retrieve(card_number, security_code, expiry_date, node_name, storage, start, end):
    address = hash_function(card_number, security_code, expiry_date)
    index = address - start
    if start <= address <= end:
        if 0 <= index < len(storage):
            if storage[index] and storage[index][0] == card_number and storage[index][1] == security_code and storage[index][2] == expiry_date:
                print(f"[{node_name}] Dados encontrados na posição {address}: {storage[index]}. Seu cartão foi vazado. Entre em contato com nossa central para ajuda. 4002-8922")
            else:
                store_stealth(card_number, security_code, expiry_date, node_name, storage, start, end)
        else:
            print(f"[{node_name}] Erro: Índice {index} fora do intervalo.")
    else:
        forward_request(card_number, security_code, expiry_date, 'retrieve', node_name)

def forward_request(card_number, security_code, expiry_date, operation, node_name):
    target_node = "N2" if node_name == "N1" else "N1"
    target_host = NODES[target_node]["host"]
    target_port = NODES[target_node]["port"]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((target_host, target_port))
        request = {'operation': operation, 'card_number': card_number, 'security_code': security_code, 'expiry_date': expiry_date}
        s.sendall(pickle.dumps(request))
        print(f"[{node_name}] Requisição encaminhada para {target_node}.")

def print_storage(node_name, storage):
    """Imprime o armazenamento do nó."""
    print(f"[{node_name}] Estado atual do armazenamento:")
    for i, data in enumerate(storage):
        print(f"Posição {i + 1}: {data}")

def start_node(node_name, host, port, start, end):
    storage = [None] * (end - start + 1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"[{node_name}] Escutando em {host}:{port}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_request, args=(conn, addr, node_name, storage, start, end)).start()

def client():
    while True:
        print("\n----------------------Verifique em tempo real se seu cartão foi vazado na internet!----------------------")
        print("\n1: Armazenar dados do cartão")
        print("2: Consultar se meu cartão foi comprometido")
        print("3: Mostrar armazenamento")
        print("4: Sair")
        choice = input("Escolha uma opção (1/2/3/4): \n")

        if choice == '1':
            card_number = input("Digite o número do seu cartão: ")
            security_code = input("Digite o código de segurança: ")
            expiry_date = input("Digite a data de expiração (MM/AAAA): ")
            node = "N1" if hash_function(card_number, security_code, expiry_date) <= 10 else "N2"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((NODES[node]["host"], NODES[node]["port"]))
                request = {'operation': 'store', 'card_number': card_number, 'security_code': security_code, 'expiry_date': expiry_date}
                s.sendall(pickle.dumps(request))
        elif choice == '2':
            card_number = input("Digite o número do seu cartão: ")
            security_code = input("Digite o código de segurança: ")
            expiry_date = input("Digite a data de validade (MM/AAAA): ")
            node = "N1" if hash_function(card_number, security_code, expiry_date) <= 10 else "N2"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((NODES[node]["host"], NODES[node]["port"]))
                request = {'operation': 'retrieve', 'card_number': card_number, 'security_code': security_code, 'expiry_date': expiry_date}
                s.sendall(pickle.dumps(request))
        elif choice == '3':
            node = input("Digite o nome do nó (N1 ou N2): ")
            if node in NODES:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((NODES[node]["host"], NODES[node]["port"]))
                    request = {'operation': 'print_storage'}
                    s.sendall(pickle.dumps(request))
            else:
                print("Nó inválido.")
        elif choice == '4':
            print("Saindo...")
            break
        else:
            print("Opção inválida.")

if __name__ == '__main__':
    p1 = Process(target=start_node, args=("N1", "localhost", 5006, 1, 10))
    p2 = Process(target=start_node, args=("N2", "localhost", 5005, 11, 20))

    p1.start()
    p2.start()
    time.sleep(1)
    client()
    p1.terminate()
    p2.terminate()