import socket
# config
import src.config.config as c
# common
from src.common.utils import print_info
import src.common.msg as m
from src.socket.socket_node import SocketNode
from src.common.buffer_attr import serialize, deserialize
import time

class SocketClient:
    def __init__(self, name=c.NAME, addr=c.ADDR_CLIENT, port=c.PORT_INT, options=c.OPTIONS):
        self.name = name
        self.addr = addr
        self.port = port
        self.options = options
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def request(self):
        msg = self._connect_recv_msg()
        node = None
        if msg == m.READY_MSG:
            # use socket to exchange metadata of client
            node = SocketNode(name=self.name)
            server_metadata_attr = self._exchange_metadata(node)
            # qp
            node.qp2init().qp2rtr(server_metadata_attr).qp2rts()
            # exchange done, write message or push file to buffer
            msg = "a message from client"
            node.post_write(node.file_mr, msg, len(msg), server_metadata_attr.remote_stag, server_metadata_attr.addr)
            node.poll_cq()
            node.post_read(node.read_mr, c.BUFFER_SIZE, server_metadata_attr.remote_stag, server_metadata_attr.addr)
            node.poll_cq()
            msg = node.read_mr.read(c.BUFFER_SIZE, 0)
            print(msg)
        # done
        node.close()
        self._close()

    def push_file(self, local_file):
        msg = self._connect_recv_msg()
        node = None
        if msg == m.READY_MSG:
            # use socket to exchange metadata of client
            node = SocketNode(name=self.name)
            server_metadata_attr = self._exchange_metadata(node)
            # qp
            node.qp2init().qp2rtr(server_metadata_attr).qp2rts()
            # exchange done, write message or push file to buffer
            node.post_recv(node.recv_mr)
            self.socket.sendall(m.PUSH_FILE_MSG)
            node.c_push_file(local_file)
            print("push done exist")
        # done
        node.close()
        self._close()

    def pull_file(self, remote_file):
        msg = self._connect_recv_msg()
        node = None
        if msg == m.READY_MSG:
            # use socket to exchange metadata of client
            node = SocketNode(name=self.name)
            server_metadata_attr = self._exchange_metadata(node)
            # qp
            node.qp2init().qp2rtr(server_metadata_attr).qp2rts()
            # exchange done, write message or push file to buffer
            node.post_recv(node.recv_mr)
            self.socket.sendall(m.PULL_FILE_MSG)
            node.c_pull_file(remote_file)
            print("pull done exist")
        node.close()
        # done
        self._close()
    #NFS read 
    def new_pull_file(self, remote_file):
        msg = self._connect_recv_msg() #begin, ready 
        node = None
        if msg == m.READY_MSG:
            # use socket to exchange metadata of client
            node = SocketNode(name=self.name)
            server_metadata_attr = self._exchange_metadata(node)
            # qp
            node.qp2init().qp2rtr(server_metadata_attr).qp2rts() #qp gid
            # exchange done, write message or push file to buffer
            node.post_recv(node.recv_mr)
            time.sleep(3)
            print("start to send file")
            self.socket.sendall(m.SEND_FILE_MSG)
            print("start read file"+str(time.perf_counter()))
            node.c_init_send(remote_file)
            print("end read file"+str(time.perf_counter()))
            # todo in socket_node
        node.close()
        # done
        self._close()
    def _exchange_metadata(self, node: SocketNode):
        buffer_attr_bytes = serialize(node.buffer_attr)
        self.socket.sendall(buffer_attr_bytes)
        # get the metadata from server
        server_metadata_attr_bytes = self.socket.recv(c.BUFFER_SIZE)
        server_metadata_attr = deserialize(server_metadata_attr_bytes)
        print_info("server metadata attr:\n" + str(server_metadata_attr))
        return server_metadata_attr

    def _connect_recv_msg(self):
        print("connect in", self.addr, self.port)
        self.socket.connect((self.addr, self.port))
        self.socket.sendall(m.BEGIN_MSG)
        msg = self.socket.recv(c.BUFFER_SIZE)
        return msg

    def _close(self):
        self.socket.sendall(m.DONE_MSG)
        self.socket.close()
