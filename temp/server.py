#!/usr/bin/env python
 
 
# common
import socketserver
# config
from typing import Any
import src.config.config as c
from src.common.utils import print_info
import src.common.msg as m
from src.socket.socket_node import SocketNode
from src.common.buffer_attr import serialize, deserialize
 


# multi thread
class HandleServer(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        print("\n---------------------------- A CONNECT ACCEPT  --------------------------------")
        conn = self.request
        #TODO: here, how to bring the name into the handle func
        node = SocketNode(c.NAME)
 
        while True:
            try:
                # conn = self.request
                # node = SocketNode(c.NAME)
                msg = conn.recv(c.BUFFER_SIZE)
                if msg == m.BEGIN_MSG:
                    print("begin, exchange the metadata")
                    conn.sendall(m.READY_MSG)
                    # exchange the metadata
                    # use socket to exchange the metadata of server
                    client_metadata_attr_bytes = conn.recv(c.BUFFER_SIZE)
                    self.client_metadata_attr = deserialize(client_metadata_attr_bytes)
                    print_info("the client metadata attr is:\n" + str(self.client_metadata_attr))
                    # qp_attr
                    node.qp2init().qp2rtr(self.client_metadata_attr).qp2rts()
                    # node.post_recv(node.recv_mr)
                    # send its buffer attr to client
                    buffer_attr_bytes = serialize(node.buffer_attr)
                    conn.sendall(buffer_attr_bytes)
                    # exchange metadata done
                    # node.poll_cq()
                # elif msg == m.FORWARD_FILE_MSG:
                #     node.p_receive_send()
                #     print("receive client send")
                
                elif msg == m.PUSH_FILE_MSG:
                    node.s_save_file()
                    print("success save file")
                elif msg == m.PULL_FILE_MSG:
                    node.s_push_file()
                    print("success server push file")
                elif msg == m.SEND_FILE_MSG:
                    print("start to read file")
                    node.s_receive_file_send(self.client_metadata_attr)
                    print("success write file to client")
                elif msg == m.DONE_MSG:
                    print("done")
                    node.close()
                    break
                elif msg == m.SEND_FILE_OP_MSG:
                    # print("for file operation")
                    node.s_receive_file_send(self.client_metadata_attr)
                    # print(" file operation ok!")                    
                    node.close()
            except Exception as err:
                print(err)
                node.close()
                break
        print("---------------------------- A CONNECT DONE  --------------------------------")


# connection establish use socket, then use ibv to rdma
class SocketServer:
    def __init__(self, name=c.NAME, addr=c.ADDR_SERVER, port=c.PORT_INT, options=c.OPTIONS):
        self.server = socketserver.ThreadingTCPServer((addr, port,), HandleServer)
        print("listening in", addr, port)
        self.name = name
        self.options = options

    def serve(self):
        self.server.serve_forever()
 