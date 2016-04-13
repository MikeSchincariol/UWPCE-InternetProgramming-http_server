import socket
import sys
import os.path
import glob
import mimetypes
import datetime


def response_ok(body=b"this is a pretty minimal response", mimetype=b"text/plain"):
    """returns a basic HTTP response"""
    resp = []
    resp.append(b"HTTP/1.1 200 OK")
    resp.append(b"".join([b"Content-Type: ", mimetype]))
    resp.append(b"")
    resp.append(body)
    return b"\r\n".join(resp)


def response_method_not_allowed():
    """returns a 405 Method Not Allowed response"""
    resp = []
    resp.append(b"HTTP/1.1 405 Method Not Allowed")
    resp.append(b"")
    return b"\r\n".join(resp)


def response_not_found():
    """returns a 404 Not Found response"""
    resp = []
    resp.append(b"HTTP/1.1 404 Not Found")
    resp.append(b"")
    return b"\r\n".join(resp)

def response_unsupported_media_type():
    """Returns 415 Unsupported Media Type response"""
    resp = []
    resp.append(b"HTTP/1.1 415 Unsupported Media Type")
    resp.append(b"")
    return b"\r\n".join(resp)


def parse_request(request):
    first_line = request.split("\r\n", 1)[0]
    method, uri, protocol = first_line.split()
    if method != "GET":
        raise NotImplementedError("We only accept GET")
    return uri


def resolve_uri(uri, webroot="."):
    """Returns the content and mime-type of the resource point to by the uri.
       If the URI is a directory, a textual listing of the directory is returned.
       If the URI is a file, the file contents are returned if it has a known mime-type.
       If the URI is found but it is not a directory or file, or the file is not a known mime-type.
          a TypeError exception is raised that can be trapped for by the caller.
       If the URI does not exist, a NameError exception is raised that can be trapped for by the caller.

    :param webroot: The root directory to search for resources from.
    :param uri: The resource requested as a relative path from webroot.
    :return: The content and mime-type as a tuble.
    """

    # Jail the URI resolution to start from webroot
    startup_dir = os.path.abspath(os.curdir)
    os.chdir(webroot)
    # The leading slash in the uri causes os.path.join to return the root directory "/"
    # which is a big security concern. To get around this, append the local directory
    # "." so that everything is relative to the current directory.
    relative_uri = "." + uri
    resp = []
    if not(os.path.exists(relative_uri)):
        # Path doesn't exist. Toss an exception to notify the client.
        os.chdir(startup_dir)
        raise NameError("The URI: {} does not exist".format(uri))
    elif os.path.isdir(relative_uri):
        # Get a listing of the directory, convert each string entry to bytes
        # and send it back to the caller with the mimetype of text/plain
        os.chdir(relative_uri)
        dirlist = glob.glob("*")
        for item in dirlist:
            resp.append(item.encode('utf8'))
        mimetype = ("text/plain", None)
    elif os.path.isfile(relative_uri):
        # Get the file contents and return it as bytes
        filename = os.path.basename(relative_uri)
        mimetype = mimetypes.guess_type(filename)
        if mimetype is None:
            # Path / item exists but the server can't handle it's content type
            raise TypeError("The URI is valid but the server does not support the media type")
        elif mimetype[0] == "text/plain":
            # For plaintext files, must convert characters to bytes before
            # sending.
            with open(relative_uri, "r") as fh:
                resp.append(fh.read().encode('utf8'))
        else:
            # For non-text files, just use their contents directly as the body
            # of the HTTP message. Ensure the body ends with a CRLF.
            with open(relative_uri, "rb") as fh:
                resp.append(fh.read())
    else:
        # Path / item exists but the server can't handle it's content type
        os.chdir(startup_dir)
        raise TypeError("The URI is valid but the server does not support the media type")

    os.chdir(startup_dir)
    return b"\r\n".join(resp), mimetype[0].encode('utf8')

def server(log_buffer=sys.stderr, webroot=os.path.abspath(os.path.join(os.path.curdir, "webroot"))):
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
            try:
                print('connection - {0}:{1}'.format(*addr), file=log_buffer)
                request = ''
                while True:
                    data = conn.recv(1024)
                    request += data.decode('utf8')
                    if len(data) < 1024:
                        break

                try:
                    uri = parse_request(request)
                except NotImplementedError:
                    response = response_method_not_allowed()
                else:
                    try:
                        content, mime_type = resolve_uri(uri, webroot)
                    except NameError:
                        response = response_not_found()
                    except TypeError:
                        response = response_unsupported_media_type()
                    else:
                        response = response_ok(content, mime_type)

                print('sending response', file=log_buffer)
                conn.sendall(response)
            finally:
                conn.close()

    except KeyboardInterrupt:
        sock.close()
        return


if __name__ == '__main__':
    server()
    sys.exit(0)
