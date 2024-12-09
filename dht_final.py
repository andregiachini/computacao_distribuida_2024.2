import socket
import threading
import pickle
from multiprocessing import Process
import time

# Configurações dos nós
NODES = {
    "N1": {"host": "localhost", "port": 5006, "start": 1, "end": 10},
    "N2": {"host": "localhost", "port": 5005, "start": 11, "end": 20},
}

def hash_function(rg):
    """Função hash para calcular a posição de armazenamento."""
    return (rg % 20) + 1

def handle_request(conn, addr, node_name, storage, start, end):
    """Lida com as requisições recebidas pelo nó."""
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            request = pickle.loads(data)
            operation = request['operation']
            rg = request['rg']
            name = request.get('name')

            if operation == 'store':
                store(rg, name, node_name, storage, start, end)
            elif operation == 'retrieve':
                retrieve(rg, node_name, storage, start, end)
        except Exception as e:
            print(f"[{node_name}] Erro: {e}")
            break
    conn.close()

def store(rg, name, node_name, storage, start, end):
    """Armazena o RG e o nome na posição correta."""
    address = hash_function(rg)
    index = address - start
    if start <= address <= end:
        if 0 <= index < len(storage):
            if storage[index] is None:
                storage[index] = (rg, name)
                print(f"[{node_name}] RG {rg} armazenado na posição {address}.")
            else:
                print(f"[{node_name}] Colisão na posição {address}. Tentando próxima posição...")
                for i in range(index + 1, index + 1 + len(storage)):
                    circular_index = i % len(storage)
                    if storage[circular_index] is None:
                        storage[circular_index] = (rg, name)
                        print(f"[{node_name}] RG {rg} armazenado na posição {start + circular_index}.")
                        return
                print(f"[{node_name}] Erro: Não há espaço disponível para armazenar RG {rg}.")
        else:
            print(f"[{node_name}] Erro: Índice {index} fora do intervalo.")
    else:
        forward_request(rg, name, 'store', node_name)

def retrieve(rg, node_name, storage, start, end):
    """Busca um RG na tabela."""
    address = hash_function(rg)
    index = address - start
    if start <= address <= end:
        if 0 <= index < len(storage):
            if storage[index] and storage[index][0] == rg:
                print(f"[{node_name}] RG {rg} encontrado na posição {address}: {storage[index][1]}")
            else:
                print(f"[{node_name}] RG {rg} não encontrado na posição {address}.")
        else:
            print(f"[{node_name}] Erro: Índice {index} fora do intervalo.")
    else:
        forward_request(rg, None, 'retrieve', node_name)

def forward_request(rg, name, operation, node_name):
    """Encaminha a requisição para o outro nó."""
    target_node = "N2" if node_name == "N1" else "N1"
    target_host = NODES[target_node]["host"]
    target_port = NODES[target_node]["port"]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((target_host, target_port))
        request = {'operation': operation, 'rg': rg, 'name': name}
        s.sendall(pickle.dumps(request))
        print(f"[{node_name}] Requisição encaminhada para {target_node}.")

def start_node(node_name, host, port, start, end):
    """Inicia o servidor do nó."""
    storage = [None] * (end - start + 1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"[{node_name}] Escutando em {host}:{port}...")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_request, args=(conn, addr, node_name, storage, start, end)).start()

def client():
    """Cliente interativo para enviar requisições aos nós."""
    while True:
        print("\n1: Armazenar RG")
        print("2: Consultar RG")
        print("3: Sair")
        choice = input("Escolha uma opção (1/2/3): ")

        if choice == '1':
            rg = int(input("Digite o RG: "))
            name = input("Digite o nome: ")
            node = "N1" if rg <= 10 else "N2"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((NODES[node]["host"], NODES[node]["port"]))
                request = {'operation': 'store', 'rg': rg, 'name': name}
                s.sendall(pickle.dumps(request))
        elif choice == '2':
            rg = int(input("Digite o RG para consulta: "))
            node = "N1" if rg <= 10 else "N2"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((NODES[node]["host"], NODES[node]["port"]))
                request = {'operation': 'retrieve', 'rg': rg}
                s.sendall(pickle.dumps(request))
        elif choice == '3':
            print("Saindo...")
            break
        else:
            print("Opção inválida.")

if __name__ == '__main__':
    # Inicia os nós em processos separados
    p1 = Process(target=start_node, args=("N1", "localhost", 5006, 1, 10))
    p2 = Process(target=start_node, args=("N2", "localhost", 5005, 11, 20))

    p1.start()
    p2.start()

    # Aguarda um tempo para garantir que os nós estão rodando
    time.sleep(1)

    # Inicia o cliente interativo
    client()

    # Finaliza os processos dos nós
    p1.terminate()
    p2.terminate()