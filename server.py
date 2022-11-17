#!/bin/python3

import comm
import argparse
import subprocess
from socket import socket
from threading import Thread
from select import select

def handle_client(conn):
    rlist, wlist, xlist = select([conn], [], [], 5.0)

    # Mostra o banner do servidor e sai se o cliente demorar mais de 0.5 segundos
    if len(rlist) == 0:
        conn.send(b'DistRunner\'s executor server\n')
        conn.close()
        return

    # Recebe opcoes antes de receber o comando para ser rodado
    token = b''
    while True:
        token = comm.recv_token(conn)
        if token == b'OPT':
            option = comm.recv_data(conn)
            if option == b'tunnel_stdin':
                print('Opcao tunnel_stdin setada')
            else:
                conn.send(b'ERR')
                conn.close()
                return
        else:
            break

    # Recebe o comando
    command = b''
    if token == b'CMD':
        command = comm.recv_data(conn)
    else:
        conn.send(b'ERR')
        conn.close()
        return

    # Roda o programa
    program = subprocess.Popen(command.split(b' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    (pin, pout) = (program.stdin, program.stdout)

    while True:
        outs = select([conn, pout], [], [])[0]

        # Tem coisa para ser lida no socket
        if conn in outs:
            try:
                buffer = comm.recv_data(conn, token=b'INP')
                pin.write(buffer)
            except EOFError:
                break

        # Tem coisa para ser lida no processo
        if pout in outs:
            buff = b''
            while True:
                tmp_buff = pout.read(512)
                buff += tmp_buff
                if len(tmp_buff) < 512:
                    break

            # Se for EOF, sair
            if len(buff) == 0:
                break

            comm.send_data(conn, buff, token=b'OUT')

    conn.close()

argument_parser = argparse.ArgumentParser(prog='DistRunnerServer', description='DistRunner Executor Server')
argument_parser.add_argument('-a', '--bind-address', default='0.0.0.0', help='Address to bind server to. Default: 0.0.0.0')
argument_parser.add_argument('-p', '--port', default=56789, type=int, help='Port to run server on. Default: 56789')
argument_parser.add_argument('-C', '--command-allowlist', help='Allow only commands on this file to be run. If none, allow all commands')
argument_parser.add_argument('-A', '--address-allowlist', help='Allow only addresses on this file to connect. If none, allow anyone to connect')

def main():
    args = argument_parser.parse_args()

    with socket() as s:
        s.bind((args.bind_address, args.port))
        s.listen()
        while True: # Cria uma thread para cada conexao que chega
            conn, addr = s.accept()
            print(f'Incomming connection from {addr}')
            t = Thread(target=handle_client, args=[conn])
            t.daemon = True
            t.start()

if __name__ == '__main__':
    main()
