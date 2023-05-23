import socket
import ssl
import base64
import codecs
import time
import zlib

from address import Address
from cache import Cache
from header import Header
from token import Token, Text, Tag


class RequestHandler:

    def __init__(self):
        self.url_cache = Cache()

    def request(self, url: str, header_list: list[Header] = None) -> (str, str):
        def parse_url(address):
            # separate the host from the path
            host, path = address.split("/", 1)
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
            request_bytes = "GET {} HTTP/1.1\r\n".format(path).encode("utf8") + "Host: {}\r\n".format(host).encode(
                "utf8")
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
            response = s.makefile("rb", newline="\r\n")
            # split response into pieces
            statusline = response.readline()
            version, status, explanation = statusline.split(b" ", 2)
            is_redirect = False
            try:
                assert status.decode('utf-8') == "200", "{}: {}".format(status, explanation)
            except AssertionError:
                decoded_status = int(status.decode('utf-8'))
                if decoded_status >= 300 or decoded_status < 400:
                    is_redirect = True
                else:
                    raise AssertionError
            # find all the headers
            headers = {}
            while True:
                line = response.readline()
                if line == b"\r\n":
                    break
                header, value = line.split(b":", 1)
                header = header.decode("utf8")
                value = value.decode("utf8")
                headers[header.lower()] = value.strip()
            # check if it is a redirect
            if is_redirect:
                new_url = headers['location']
                s.close()
                if new_url.startswith('/'):
                    new_url = host + new_url
                    return parse_url(new_url)
                else:
                    return self.request(new_url)
            # check for transfer encoding
            if 'transfer-encoding' in headers and headers['transfer-encoding'] == 'chunked':
                chunks = []
                chunk_length = 10
                while chunk_length > 0:
                    line = response.readline().decode('utf8')
                    line.replace('\r\n', '')
                    chunk_length = int(line, 16)
                    chunk = response.read(chunk_length)
                    chunks.append(chunk)
                    response.readline()
                body = b''.join(chunks)
            else:
                body = response.read()
            # check for content encoding - decompress and then decode
            if 'content-encoding' in headers and headers['content-encoding'] == 'gzip':
                body = zlib.decompressobj(32).decompress(body)
            body = body.decode('utf8')
            s.close()
            # Add Caching support
            if 'cache-control' in headers:
                # check if max-age is present
                max_age_present = False
                possible_position = headers['cache-control'].find('max-age=')
                total_substring = 'max-age=0'
                if possible_position != -1 and headers['cache-control'][possible_position + 9].isdigit():
                    total_substring = 'max-age='
                    rest_of_header = headers['cache-control'][possible_position + 8:]
                    for char in rest_of_header:
                        if char.isdigit():
                            total_substring += char
                        else:
                            break
                    max_age_present = True
                # check if no-store is present
                no_store_present = 'no-store' in headers['cache-control']
                if max_age_present and not no_store_present:
                    max_age = total_substring.replace('max-age=', '')
                    age = 0
                    if 'age' in headers:
                        age = headers['age']
                    expiration_time = int(time.time()) + int(max_age) - int(age)
                    address = Address(url, expiration_time, headers, body)
                    self.url_cache.add_address(address)
            return headers, body

        def parse_file(path):
            with open(path, 'r') as file:
                # Read the contents of the file
                file_contents = file.read()
            return "", file_contents

        def parse_data():
            # extract MIME type, Optional Parameters, and Content
            split_parts = url.split(',')
            non_content = split_parts[0].split(':')[0].split(';')
            mime_type = non_content[0]
            optional_parameters = []
            if len(non_content) > 1:
                optional_parameters = non_content[1:]
            content = split_parts[1]

            # helper functions
            def find_encoding(default_encoding):
                encoding = default_encoding
                for param in optional_parameters:
                    if param.startswith("charset="):
                        encoding = param.split('=')[1]
                        break
                return encoding

            def find_base():
                base = None
                for param in optional_parameters:
                    if param.startswith("base"):
                        return param
                return base

            # cases for all MIME types
            decoded_data = content
            # figure out encoding
            # decode the data
            # figure out how to represent the data based on the mime type
            # handle the optional parameters
            # error handling for unsupported types
            match mime_type:
                case 'text/plain':
                    baseX = find_base()
                    if not (baseX is None):
                        if baseX == 'base64':
                            decoded_bytes = base64.b64decode(content)
                            decoded_data = codecs.decode(decoded_bytes, "utf-8")
                case 'text/html':
                    baseX = find_base()
                    if not (baseX is None):
                        if baseX == 'base64':
                            decoded_bytes = base64.b64decode(content)
                            decoded_data = codecs.decode(decoded_bytes, "utf-8")
                case 'image/jpeg' | 'image/png':
                    decoded_data = base64.b64decode(content)
                case 'application/pdf' | 'application/json' | 'audio/mpeg' | 'video/mp4':
                    print("The MIME type entered in the URL is not currently supported.")
                case _:
                    print("The MIME type entered in the URL is not supported.")
            return "", decoded_data

        def transform_source(body):
            new_body = "<body>"
            for c in body:
                if c == "<":
                    new_body += '&lt;'
                elif c == ">":
                    new_body += '&gt;'
                else:
                    new_body += c
            new_body += "</body>"
            return new_body

        # strip off the http or https portion
        scheme, url = url.split(":", 1)
        assert scheme in ["http", "https", "file", "data", "view-source"], \
            "Unknown scheme {}".format(scheme)
        match scheme:
            case "http" | "https":
                url = url[2:]
                # Return from cache if the address is not past its expiration date
                cached_address = self.url_cache.get_address(url)
                if cached_address:
                    if self.url_cache.is_address_expired(cached_address):
                        return cached_address.headers, cached_address.body
                    else:
                        self.url_cache.delete_address(url)
                # If not in cache, proceed normally
                return parse_url(url)
            case "file":
                url = url[2:]
                return parse_file(url)
            case "data":
                return parse_data()
            case "view-source":
                inner_scheme, inner_url = url.split(":", 1)
                scheme = inner_scheme
                url_headers, url_body = parse_url(inner_url[2:])
                return url_headers, transform_source(url_body)

    def lex(self, body: str) -> [Token]:
        out = []
        content = ""
        in_tag = False
        in_body = False
        last_seven_chars = "       "
        for c in body:
            last_seven_chars = (last_seven_chars + c)[-7:]
            # check if inside the body tags to ignore style
            if last_seven_chars[-5:] == "<body":
                in_body = True
            elif last_seven_chars[-5:] == "/body>":
                in_body = False
            # check if an angle brackets
            if c == "<":
                in_tag = True
                if content:
                    out.append(Text(content))
                content = ""
            elif c == ">":
                in_tag = False
                out.append(Tag(content))
                content = ""
            elif in_body:
                content += c
                if content[-4:] == '&lt;':
                    content = content[:-4] + '<'
                elif content[-4:] == '&gt;':
                    content = content[:-4] + '>'
        if not in_tag and content and in_body:
            out.append(Text(content))
        return out

# if __name__ == "__main__":
#     # create default file to open when no url is passed in
#     current_path = os.getcwd()
#     with open(current_path + '/panda_surf_df.txt', 'w') as default_file:
#         # Perform any write operations on the file
#         default_file.write("This is the PandaSurf Default File.\n")
#     # open the url or file path
#     import sys
#     rq = RequestHandler()
#     try:
#         if sys.argv is not None:
#             rq.load(sys.argv[1])
#     except IndexError:
#         rq.load()
