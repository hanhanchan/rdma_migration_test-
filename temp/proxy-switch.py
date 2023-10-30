import socket
# config
import src.config.config as c
# common
import socketserver
# config
from typing import Any
import src.config.config as c
from src.common.utils import print_info
import src.common.msg as m
from src.socket.socket_node import SocketNode
from src.common.buffer_attr import serialize, deserialize
import pickle
import time 
import argparse
import os
import sys
from time import sleep

import grpc

# Import P4Runtime lib from parent utils dir
# Probably there's a better way of doing this.
sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '../utils/'))
import p4runtime_lib.bmv2
import p4runtime_lib.helper
from p4runtime_lib.error_utils import printGrpcError
from p4runtime_lib.switch import ShutdownAllSwitchConnections
p4info_file_path='src/socket/simple-version-modify-header.p4.p4info.txt'
bmv2_file_path='src/socket/simple-version-modify-header.json'
threading_index=-1
port=50051
class fileobject:
    def __init__(self,path,host_server=0):
        self.path=str(path)
        self.host_server=host_server
class SocketClient:
    def __init__(self, name=c.NAME, addr=None, port=c.PORT_INT, options=c.OPTIONS):
        self.name = name
        self.addr = addr
        self.port = port
        self.options = options
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.node = None
        self.server_metadata_attr=None
    def request(self):
        msg = self._connect_recv_msg()
 
        if msg == m.READY_MSG:
            # use socket to exchange metadata of client
            self.node = SocketNode(name=self.name)
            server_metadata_attr = self._exchange_metadata(self.node)
            # qp
            self.node.qp2init().qp2rtr(server_metadata_attr).qp2rts()
            # exchange done, write message or push file to buffer
        # done
        # node.close()
        # self._close()
        return server_metadata_attr
    def _exchange_metadata(self, node: SocketNode):
        buffer_attr_bytes = serialize(node.buffer_attr)
        self.socket.sendall(buffer_attr_bytes)
        # get the metadata from server
        server_metadata_attr_bytes = self.socket.recv(c.BUFFER_SIZE)
        self.server_metadata_attr = deserialize(server_metadata_attr_bytes)
        print_info("server metadata attr:\n" + str(self.server_metadata_attr))
        return self.server_metadata_attr

    def _connect_recv_msg(self):
        print("connect in", self.addr, self.port)
        self.socket.connect((self.addr, self.port))
        self.socket.sendall(m.BEGIN_MSG)
        msg = self.socket.recv(c.BUFFER_SIZE)
        return msg

    def _close(self):
        self.socket.sendall(m.DONE_MSG)
        self.socket.close()
class CreateControl():
    def __init__(self):
        if c.is_control_plane!=True:
            global threading_index                                   
            self.p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)
            self.s1 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
                name='s1',
                address='192.168.56.10:50051',
                device_id=1,
                proto_dump_file='logs/s1-p4runtime-requests.txt')
            self.s1.MasterArbitrationUpdate()
            self.s1.SetForwardingPipelineConfig(p4info=self.p4info_helper.p4info,
                                            bmv2_json_file_path=bmv2_file_path)
            print("Installed P4 Program using SetForwardingPipelineConfig on s1")
    def writeQPrules(self,client_qp,host_src_ip,index):
        # 1) match server B, rewrite dst from server A to client 
        table_entry = self.p4info_helper.buildTableEntry(
            table_name="MyIngress.record_port",
            match_fields={

                "hdr.ib_bth.dst_qp": client_qp,
                "hdr.ipv4.dst_addr": (host_src_ip, 32),                
            },
            action_name="MyIngress.record_switch_port",
            action_params={
                "index":index,
            }
            )
        self.s1.WriteTableEntry(table_entry)
        print("Installed ingress QP rule on %s" % self.s1.name)
    def writeIPRules(self,rswitch_ip_addr,rhost_ip_addr,rswitch_mac,rhost_mac,rqp_index,rclient_qp,index):
        # 1) match server B, rewrite dst from server A to client 
        table_entry =self.p4info_helper.buildTableEntry(
            table_name="MyIngress.ipv4_lpm",
            match_fields={
                "hdr.ipv4.dst_addr": (rswitch_ip_addr, 32),
                "hdr.ib_bth.dst_qp": rqp_index,
            },
            action_name="MyIngress.ipv4_forward",
            action_params={
                "switch_ip":rswitch_ip_addr, 
                "host_ip":rhost_ip_addr, 
                "switch_mac":rswitch_mac,
                "host_mac":rhost_mac,
                "client_qp":rclient_qp,
                "port_index":index,
            })
        self.s1.WriteTableEntry(table_entry)
        print("Installed ingress tunnel rule on %s" % self.s1.name)
    def writeTunnelRules(self,rclient_address,rclient_qp,rkey,raddr):
        # 1) match server B, rewrite dst from server A to client 
        table_entry = self.p4info_helper.buildTableEntry(
            table_name="MyEgress.rdma_translate",
            match_fields={
                "hdr.ipv4.dst_addr": (rclient_address, 32),
                "hdr.ib_bth.dst_qp": rclient_qp,
            },
            action_name="MyEgress.translate",
            action_params={
                "mount_raddr": raddr,
                "mount_rkey": rkey
            })
        self.s1.WriteTableEntry(table_entry)
        print("Installed egress translate rule on %s" % self.s1.name)
p4control=CreateControl()     
class HandleServer(socketserver.BaseRequestHandler):
 
 
    def handle(self) -> None:
        #get client port
        # print(type(self.client_address))
        # print(self.client_address[0])
        # print(self.client_address[1])
        # socket = self.request 
        # print(socket.getsockname())
        global threading_index
        global p4control
        threading_index=threading_index+1
        print("now threading index is "+str(threading_index))
        print("\n---------------------------- A CONNECT ACCEPT  --------------------------------")
        self.client_1=SocketClient(addr=c.ADDR_CLIENT_1)
        self.client_1.request()
        self.client_2=SocketClient(addr=c.ADDR_CLIENT_2)
        self.client_2.request()
        conn = self.request
        # # TODO: here, how to bring the name into the handle func
        node = SocketNode(c.NAME)
        while True:
            try:
                # conn = self.request
                # self.client=SocketClient()
                # self.client.request()
                # # TODO: here, how to bring the name into the handle func
                # node = SocketNode(c.NAME)
                msg = conn.recv(c.BUFFER_SIZE)
                if msg == m.BEGIN_MSG:
                    print("begin, exchange the metadata")
                    conn.sendall(m.READY_MSG)
                    # exchange the metadata
                    # use socket to exchange the metadata of server
                    client_metadata_attr_bytes = conn.recv(c.BUFFER_SIZE)
                    self.client_metadata_attr = deserialize(client_metadata_attr_bytes)
                    #write client to switch
                    print_info("the client metadata attr is:\n" + str(self.client_metadata_attr))
                    #todo: here to add rewrite rules
                    # qp_attr
                    node.qp2init().qp2rtr(self.client_metadata_attr).qp2rts()
                    # node.post_recv(node.recv_mr)
                    # send its buffer attr to client
                    buffer_attr_bytes = serialize(node.buffer_attr)
                    conn.sendall(buffer_attr_bytes)
                    # exchange metadata done
                    # node.poll_cq()
                    if c.is_control_plane!=True:
                        #from switch to client 
                        switch_ip_addr="192.168.56.10"
                        client_ip_addr="192.168.56.2"
                        switch_mac="08:00:27:5f:2e:f6"
                        host_mac="08:00:27:4f:de:53"
                        
                        #convert pairs
                        #server2 to switch 
                        server2_switch_qp=self.client_2.node.buffer_attr.qp_num
                        # switch to client
                        switch_client_qp=self.client_metadata_attr.qp_num
                        
                        p4control.writeQPrules(self.client_metadata_attr.qp_num,client_ip_addr,threading_index)

                        p4control.writeIPRules(switch_ip_addr,client_ip_addr,
                        switch_mac,host_mac,server2_switch_qp,switch_client_qp,threading_index)

                        #modify port qp and port 
                    
                        p4control.writeTunnelRules(client_ip_addr,switch_client_qp,self.client_metadata_attr.remote_stag,self.client_metadata_attr.addr)#remote_info[i]['rkey'], remote_info[i]['addr'])
                        print("write switch rules ok!")
                elif msg == m.SEND_FILE_MSG:
                    #print("-----------receive from client-------")
                    content=node.p_receive_client()
                    #print(pickle.loads(content))
 
                    #print("-----------requires for meta--------") 
                    self.client_1.node.post_recv(self.client_1.node.recv_mr)
                    self.client_2.node.post_recv(self.client_2.node.recv_mr)
                    
                    self.client_1.socket.sendall(m.SEND_FILE_META_MSG)
 
                    content=self.client_1.node.send_for_meta(content)
  
                    # emit check host server 
                    #print("-----------requires for read file--------") 
                    self.client_2.socket.sendall(m.SEND_FILE_OP_MSG)
                    file_stream=self.client_2.node.send_for_file(content)
                   # print("file_stream ok!")
                    if c.is_control_plane==True:
                        node.p_return_write(file_stream,self.client_metadata_attr)
                    #s.node,s.client_metadata_attr,c.node,c.server_metadata_attr
                    # print("success write file to client")
                elif msg == m.DONE_MSG:
                    print("done")
                    node.close()
                    break
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
        # connect to bmv2 
        

    def serve(self):
 
        self.server.serve_forever()

 