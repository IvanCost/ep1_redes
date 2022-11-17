def send_token(sock, token):
    sock.send(token)

def recv_token(sock):
    token = sock.recv(3)
    if len(token) == 0:
        raise EOFError
    return token

def expect_token(sock, expected_token):
    token = recv_token(sock)
    if token != expected_token:
        raise RuntimeError('Token inválido')

def recv_int(sock, *, token: bytes = None):
    if token is not None:
        expect_token(sock, token)

    val = sock.recv(4)
    if len(val) == 0:
        raise EOFError
    return int.from_bytes(val, 'big') # Big endian, que é o padrão da rede

def send_int(sock, val: int, *, token: bytes = None):
    if token is not None:
        send_token(sock, token)

    buff = val.to_bytes(4, 'big')
    return sock.send(buff)

def recv_data(sock, *, token: bytes = None):
    if token is not None:
        expect_token(sock, token)

    length_left = recv_int(sock)

    buff = b''
    while length_left != 0:
        tmp_buff = sock.recv(length_left)
        if len(tmp_buff) == 0:
            raise EOFError
        length_left -= len(tmp_buff)
        buff += tmp_buff

    return buff

def send_data(sock, data: bytes, *, token: bytes = None):
    if token is not None:
        send_token(sock, token)

    send_int(sock, len(data))
    return sock.send(data)

