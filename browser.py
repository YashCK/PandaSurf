import os
import socket
import ssl

from header import Header


def request(url: str, header_list: list[Header] = None) -> (str, str):
    def parse_url():
        # separate the host from the path
        host, path = url.split("/", 1)
        path = "/" + path
        # support custom ports
        if ":" in host:
            host, custom_port = host.split(":", 1)
            port = int(custom_port)
        else:
            port = 80 if scheme == "http" else 443
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
        s.connect((host, port))
        # make request to other server
        connection = "close"
        request_bytes = "GET {} HTTP/1.1\r\n".format(path).encode("utf8") + "Host: {}\r\n".format(host).encode("utf8")
        connection_header = "Connection: {}\r\n\r\n".format(connection).encode("utf8")
        if not (header_list is None):
            for head in header_list:
                if head.name == "Connection":
                    connection_header = "Connection: {}\r\n\r\n".format(head.value).encode("utf8")
                    continue
                heading = head.name + ": {}\r\n"
                request_bytes += heading.format(head.value).encode("utf8")
        request_bytes += connection_header
        s.send(request_bytes)
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
        print("hiiiii")
        print("headers: ", headers)
        print("body: ", body)
        return headers, body

    def parse_file(path):
        with open(path, 'r') as file:
            # Read the contents of the file
            file_contents = file.read()
        return "abcd", file_contents

    # strip off the http or https portion
    scheme, url = url.split("://", 1)
    assert scheme in ["http", "https", "file"], \
        "Unknown scheme {}".format(scheme)
    match scheme:
        case "http" | "https":
            return parse_url()
        case "file":
            return parse_file(url)


def show(body: str):
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            print(c, end="")


def load(url: str = None):
    try:
        if url is None:
            url = "file://" + os.getcwd() + '/panda_surf_df.txt'
        header_list = [Header("User-Agent", "This is the PandaSurf Browser.")]
        headers, body = request(url, header_list)
        show(body)
    except FileNotFoundError:
        print("The path to the file you entered does not exist.")
    # except ValueError:
    #     print("The path entered was likely not in the correct format.")


if __name__ == "__main__":
    # create default file to open when no url is passed in
    current_path = os.getcwd()
    with open(current_path + '/panda_surf_df.txt', 'w') as default_file:
        # Perform any write operations on the file
        default_file.write("This is the PandaSurf Default File.\n")
    # open the url or file path
    import sys
    try:
        if sys.argv is not None:
            load(sys.argv[1])
    except IndexError:
        load()
