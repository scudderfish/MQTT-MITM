import select
import ssl
import socket
import sys
import time
from mqtt_message import MQTTControlPacket

# to resolve errno 32: broken pipe issue (only linux)
if sys.platform != 'win32':
    from signal import signal, SIGPIPE, SIG_DFL


# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
buffer_size = 4096
# buffer_size = 65535
delay = 0.0002

client_context = ssl.create_default_context()


class Forward:
    def __init__(self):
        client_context.check_hostname = False
        client_context.verify_mode = ssl.CERT_NONE
        self.forward = client_context.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM))

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception as e:
            print("\t - Grott - grottproxy forward error : ", e)
            # print(e)
            return False


class Proxy:
    input_list = []
    channel = {}

    def __init__(self, conf):
        print("\nGrott proxy mode started")

        # to resolve errno 32: broken pipe issue (Linux only)
        if sys.platform != 'win32':
            signal(SIGPIPE, SIG_DFL)
        ##

        self.server = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                                      certfile='./cert.pem', server_side=True, ssl_version=ssl.PROTOCOL_TLS)

        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # set default grottip address
        if conf.mqttip == "default":
            conf.mqttip = '0.0.0.0'
        self.server.bind((conf.mqttip, conf.mqttport))
        # socket.gethostbyname(socket.gethostname())
        try:
            hostname = (socket.gethostname())
            print("Hostname :", hostname)
            print("IP : ", socket.gethostbyname(hostname),
                  ", port : ", conf.mqttport, "\n")
        except:
            print("IP and port information not available")

        self.server.listen(200)
        self.forward_to = (conf.alip, conf.alport)

    def main(self, conf):
        self.input_list.append(self.server)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept(conf)
                    break
                try:
                    self.data, self.addr = self.s.recvfrom(buffer_size)
                except:
                    if conf.verbose:
                        print("\t - Grott connection error")
                    self.on_close(conf)
                    break
                if len(self.data) == 0:
                    self.on_close(conf)
                    break
                else:
                    self.on_recv(conf)

    def on_accept(self, conf):
        forward = Forward().start(self.forward_to[0], self.forward_to[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            if conf.verbose:
                print("\t -", clientaddr, "has connected")
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            if conf.verbose:
                print("\t - Can't establish connection with remote server."),
                print("\t - Closing connection with client side", clientaddr)
            clientsock.close()

    def on_close(self, conf):
        if conf.verbose:
            # try / except to resolve errno 107: Transport endpoint is not connected
            try:
                print("\t -", self.s.getpeername(), "has disconnected")
            except:
                print("\t -", "peer has disconnected")

        # remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self, conf):
        data = self.data
        m = MQTTControlPacket(data)
        print(m.pprint())
        # send data to destination
        self.channel[self.s].send(data)
