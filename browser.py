import socket
import ssl


def request(url):
    assert url.startswith("http://") or url.startswith("https://")
    # strip off the http or https portion
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https"], \
        "Unknown scheme {}".format(scheme)
    # separate the host from the path
    host, path = url.split("/", 1)
    path = "/" + path
    # support custom ports
    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)
    # connect socket to other computer
    s = socket.socket(
        family=socket.AF_INET,  # Over Internet
        type=socket.SOCK_STREAM,  # Can send data of arbitrary size
        proto=socket.IPPROTO_TCP,  # TCP Protocol
    )
    # encrypt the connection if https
    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)
    # connect socket to server
    port = 80 if scheme == "http" else 443
    s.connect((host, port))
    # make request to other server
    s.send("GET {} HTTP/1.0\r\n".format(path).encode("utf8") +
           "Host: {}\r\n\r\n".format(host).encode("utf8"))
    # read response
    response = s.makefile("r", encoding="utf8", newline="\r\n")
    # split response into pieces
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)
    headers = {}
    while True:
        line = response.readline()
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    assert "transfer-encoding" not in headers
    assert "content-encoding" not in headers
    body = response.read()
    s.close()
    return headers, body


def show(body):
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            print(c, end="")


def load(url):
    headers, body = request(url)
    show(body)




if __name__ == "__main__":
    import sys
    load(sys.argv[1])
