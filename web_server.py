import socket
import urllib.parse

ENTRIES = ['Panda was here']


def handle_connection(conx):
    # read the request line
    req = conx.makefile("b")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]
    # read the headers until we get to a blank line
    headers = {}
    while True:
        line = req.readline().decode('utf8')
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    # read the body once the content-length header is read
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None
    # generate a web page in response
    status, body = do_request(method, url, headers, body)
    # send page back to browser
    response = "HTTP/1.0 {}\r\n".format(status)
    response += "Content-Length: {}\r\n".format(
        len(body.encode("utf8")))
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()


def show_comments():
    out = "<!doctype html>"
    out += "<form action=add method=post>"
    out += "<p><input name=guest></p>"
    out += "<p><button>Sign the book!</button></p>"
    out += "</form>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    return out


def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()


def not_found(url, method):
    out = "<!doctype html>"
    out += "<h1>{} {} not found!</h1>".format(method, url)
    return out


def do_request(method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments()
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        return "200 OK", add_entry(params)
    else:
        return "404 Not Found", not_found(url, method)


def form_decode(body):
    # decode the request body
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        name = urllib.parse.unquote_plus(name)
        value = urllib.parse.unquote_plus(value)
        params[name] = value
    return params


# open a socket and listen for connections
if __name__ == "__main__":
    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # wait for other computers to connect (anyone can connect, port is 8000)
    s.bind(('', 8000))
    s.listen()
    # enter into a loop that runs once per connection
    while True:
        conx, addr = s.accept()
        handle_connection(conx)