import socket
import threading
import sys

class ProcessoMutexDistribuido:
    def __init__(self, id_processo, porta, peers):
        self.id_processo = id_processo
        self.porta = porta
        self.peers = peers
        self.fila_requisicoes = []
        self.em_secao_critica = False
        self.aguardando_secao_critica = False
        self.contagem_ok = 0
        self.lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("localhost", self.porta))
    
    def enviar_mensagem(self, mensagem, par):
        self.sock.sendto(mensagem.encode(), par)
        print(f"[Processo {self.id_processo}] Enviou mensagem: {mensagem} para {par}")

    def tratar_requisicao(self, id_requisitante, porta_requisitante):
        with self.lock:
            if self.em_secao_critica or self.aguardando_secao_critica:
                self.fila_requisicoes.append((id_requisitante, porta_requisitante))
                print(f"[Processo {self.id_processo}] Requisição de {id_requisitante} adicionada à fila.")
            else:
                self.enviar_mensagem("OK", ("localhost", porta_requisitante))

    def entrar_secao_critica(self):
        with self.lock:
            self.em_secao_critica = True
            print(f"[Processo {self.id_processo}] Entrando na seção crítica.")
    
    def sair_secao_critica(self):
        with self.lock:
            self.em_secao_critica = False
            print(f"[Processo {self.id_processo}] Saindo da seção crítica.")
            while self.fila_requisicoes:
                id_requisitante, porta_requisitante = self.fila_requisicoes.pop(0)
                self.enviar_mensagem("OK", ("localhost", porta_requisitante))
        for host_par, porta_par in self.peers:
            self.enviar_mensagem(f"RELEASE {self.id_processo}", (host_par, porta_par))

    def request_secao_critica(self):
        with self.lock:
            self.aguardando_secao_critica = True
        print(f"[Processo {self.id_processo}] Requisitando seção crítica.")
        self.contagem_ok = 0
        for host_par, porta_par in self.peers:
            self.enviar_mensagem(f"REQUEST {self.id_processo} {self.porta}", (host_par, porta_par))
        print(f"[Processo {self.id_processo}] Aguardando OKs dos peers...")
        while True:
            with self.lock:
                if self.contagem_ok >= len(self.peers):
                    break
        self.entrar_secao_critica()
        with self.lock:
            self.aguardando_secao_critica = False
        

    def listener(self):
        while True:
            dados, addr = self.sock.recvfrom(1024)
            mensagem = dados.decode()
            print(f"[Processo {self.id_processo}] mensagem recebida: {mensagem} de {addr}")

            partes = mensagem.split()
            if partes[0] == "REQUEST":
                id_requisitante = int(partes[1])
                porta_requisitante = int(partes[2])
                self.tratar_requisicao(id_requisitante, porta_requisitante)

            elif mensagem == "OK":
                with self.lock:
                    self.contagem_ok += 1

    def executar(self):
        threading.Thread(target=self.listener, daemon=True).start()
        while True:
            comando = input(f"[Processo {self.id_processo}] Digite 'request' para requisitar seção crítica, 'release' para liberar ou 'exit' para sair: ").strip()
            if comando.lower() == "request":
                if (not self.em_secao_critica):
                    self.request_secao_critica()
                else:
                    print(f"[Processo {self.id_processo}] Já está na região crítica.")
            elif comando.lower() == "release":
                if self.em_secao_critica:
                    self.sair_secao_critica()
                else:
                    print(f"[Processo {self.id_processo}] Não está em seção crítica.")
            elif comando.lower() == "exit":
                print(f"[Processo {self.id_processo}] Saindo.")
                break

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python nomeArquivo.py <id_processo> <porta> <localhost:porta> <localhost:porta>")
        sys.exit(1)

    id_processo = int(sys.argv[1])
    porta = int(sys.argv[2])
    peers = []
    for par in sys.argv[3:]:
        host, porta_par = par.split(":")
        peers.append((host, int(porta_par)))
    
    processo = ProcessoMutexDistribuido(id_processo, porta, peers)
    processo.executar()