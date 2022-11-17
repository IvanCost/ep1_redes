#!/bin/python3

import comm
import sys
import os
import argparse
from time import sleep
from socket import socket
from select import select
from threading import Thread

default_port = 56789

hosts = []

def load_hosts(file):
    with open(file) as f:
        for line in f:
            line = line.strip()

            if line.startswith('#') or len(line) == 0:
                continue

            address = line.split(':')

            if len(address) == 1:
                address.append(default_port)
            else:
                address[1] = int(address[1])

            hosts.append({'address': tuple(address)})

def handle_host(host):
    fifo_in = None
    input_list = [host['socket']]
    if 'fifo_path' in host:
        fifo_in = open(host['fifo_path'], 'rb', 0)
        input_list += [fifo_in]

    header = b'---%s------------------\n'%(str(host['socket'].getpeername()).encode())
    host['output'] = header

    while True:
        inputs = select(input_list, [], [])[0]

        # Tem coisa para ser lida do socket
        if host['socket'] in inputs:
            try:
                buff = comm.recv_data(host['socket'], token=b'OUT')
                host['output'] += buff
                print(header.decode() + buff.decode())
            except EOFError:
                break

        # Tem coisa para ser lida do stdin
        if fifo_in != None and fifo_in in inputs:
            buff = fifo_in.readline()

            if len(buff) == 0:
                host['socket'].close()
                break

            comm.send_data(host['socket'], buff, token=b'INP')

    if fifo_in != None:
        fifo_in.close()

argument_parser = argparse.ArgumentParser(prog='DistRunnerCli', description='CLI interface for DistRunner')
argument_parser.add_argument('-H', '--hosts-file', default='hosts.conf', help='Config file where hosts are set. Default: hosts.conf')
argument_parser.add_argument('-o', '--output', help='File where the output should be stored. Always outputs to console')
argument_parser.add_argument('-T', '--temp-dir', default='/tmp/distrunner/', help='Directory for temp files. Default: /tmp/distrunner/')
argument_parser.add_argument('-t', '--tunnel-stdin', action='store_true', help='If set, connect all remote stdin to this console\'s stdin')
argument_parser.add_argument('command', nargs=argparse.REMAINDER, help='Command to run on the remote hosts. Default: whoami')

def main():
    args = argument_parser.parse_args()

    if len(args.command) == 0:
        argument_parser.print_help()
        return

    load_hosts(args.hosts_file)

    for host in hosts:
        s = socket()
        s.connect(host['address'])
        host['socket'] = s

    if args.tunnel_stdin:
        if not os.path.exists(args.temp_dir):
            os.mkdir(args.temp_dir)

        for host in hosts:
            fifo_path = os.path.join(args.temp_dir, host["address"][0])
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)
            os.mkfifo(fifo_path)
            host['fifo_path'] = fifo_path

        for host in hosts:
            comm.send_data(host['socket'], b'tunnel_stdin', token=b'OPT')

    if args.output != None and os.path.exists(args.output):
        os.unlink(args.output)

    for host in hosts:
        comm.send_data(host['socket'], (' '.join(args.command)).encode(), token=b'CMD')

    for host in hosts:
        t = Thread(target=handle_host, args=[host])
        host['thread'] = t
        t.start()

        if args.tunnel_stdin:
            host['fifo_write'] = open(host['fifo_path'], 'wb', 0)

    while True:
        if len(hosts) == 0:
            break

        if args.tunnel_stdin:
            inputs = select([sys.stdin], [], [], 0.1)[0]

            if sys.stdin in inputs:
                line = sys.stdin.readline()

                for host in hosts:
                    host['fifo_write'].write(line.encode())

                if len(line) == 0:
                    for host in hosts:
                        host['fifo_write'].close()

        for host in hosts:
            host['thread'].join(0.1)
            if t.is_alive():
                continue
            else:
                if args.output != None:
                    with open(args.output, 'ab') as output:
                        output.write(host['output'])
                if args.tunnel_stdin:
                    os.unlink(os.path.join(args.temp_dir, host["address"][0]))
                hosts.remove(host)

if __name__ == '__main__':
    main()
