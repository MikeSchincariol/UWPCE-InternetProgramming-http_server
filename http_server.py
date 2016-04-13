import socket
import sys


def server(log_buffer=sys.stderr):
    address = ('127.0.0.1', 10001)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("making a server on {0}:{1}".format(*address), file=log_buffer)
    sock.bind(address)
    sock.listen(1)

    try:
        while True:
            print('waiting for a connection', file=log_buffer)
            conn, addr = sock.accept()  # blocking
            request = ""
            try:
                print('connection - {0}:{1}'.format(*addr), file=log_buffer)
                while True:
                    data = conn.recv(1024)
                    request += data.decode('utf8')
                    if len(data) < 1024 or not data:
                        break;
                try:
                    parse_request(request)
                except NotImplementedError:
                    response = response_method_not_allowed()
                else:
                    response = response_ok()
                print('sending response', file=log_buffer)
                conn.sendall(response)
            finally:
                conn.close()

    except KeyboardInterrupt:
        sock.close()
        return

def response_ok():
    """returns a basic HTTP response"""

    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Content-Type: text/plain",
        b"",
        b"this is a pretty minimal response"
    ])

def parse_request(request):
    first_line = request.split("\r\n", 1)[0]
    method, uri, protocol = first_line.split()
    if method != "GET":
        raise NotImplementedError("We only accept GET")
    print('request is okay', file=sys.stderr)

def response_method_not_allowed():
    """returns a 405 Method Not Allowed response"""

    response = b"\r\n".join([
        b"HTTP/1.1 405 Method Not Allowed",
        b"",
    ])

    return response


if __name__ == '__main__':
    server()
    sys.exit(0)
