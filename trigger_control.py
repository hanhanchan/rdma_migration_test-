#!/usr/bin/python3.8
import subprocess
import sys
import threading 
sys.path.append('..')

from connec_utils.connection import SKT, CM
from connec_utils.param_parser import parser  #connection parser 

from pyverbs.addr import AH, AHAttr, GlobalRoute
from pyverbs.cq import CQ
from pyverbs.device import Context
from pyverbs.enums import *
from pyverbs.mr import MR
from pyverbs.pd import PD
from pyverbs.qp import QP, QPCap, QPInitAttr, QPAttr
from pyverbs.wr import SGE, RecvWR, SendWR
#----origin controller 
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
from scapy.all import *
from scapy.contrib.roce import  *
from scapy.packet import *
SWITCH_TO_HOST_PORT = 1
SWITCH_TO_SWITCH_PORT = 2

RECV_WR = 1
SEND_WR = 2
GRH_LENGTH = 40
content=["content1","content2","content3","content4"]
mr=["mr1","mr2","mr3","mr4"]
sgl=["sgl1","sgl2","sgl3","sgl4"]
remote_info=["remote_info1","remote_info2","remote_info3","remote_info4"]
wr=["wr1","wr2","wr3","wr4"]
switch_ip_addr="192.168.56.10"
serverB_ip_addr="192.168.56.3"
serverC_ip_addr="192.168.56.4"
client_ip_addr="192.168.56.2"
# TODO: Error handling
def read_mr(mr):
    if args['qp_type'] == IBV_QPT_UD and server:
        return mr.read(mr.length - GRH_LENGTH, GRH_LENGTH).decode()
    else:
        return mr.read(mr.length, 0).decode()  
def writeIPRules(p4info_helper,sw,rswitch_ip_addr,rhost_ip_addr,rswitch_mac,rhost_mac,rswitch_port):
    # 1) match server B, rewrite dst from server A to client 
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dst_addr": (serverB_ip_addr, 32)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "switch_ip":rswitch_ip_addr, 
            "host_ip":rhost_ip_addr, 
            "switch_mac":rswitch_mac,
            "host_mac":rhost_mac,
            "switch_port":rswitch_port
        })
    sw.WriteTableEntry(table_entry)
    print("Installed ingress tunnel rule on %s" % sw.name)
def writeTunnelRules(p4info_helper,sw,rkey,raddr):
    # 1) match server B, rewrite dst from server A to client 
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyEgress.rdma_translate",
        match_fields={
            "hdr.ipv4.dst_addr": (serverC_ip_addr, 32)
        },
        action_name="MyEgress.translate",
        action_params={
            "mount_raddr": raddr,
            "mount_rkey": rkey
        })
    sw.WriteTableEntry(table_entry)
    print("Installed ingress tunnel rule on %s" % sw.name)
offload_flag=False
return_flag=True
     
if __name__ == '__main__':
    ## connect controller to switch 
    #args : connection arg
    #p4args: switch arg
    args = parser.parse_args()

    server = not bool(args['server_ip'])
    #start controller in switch 
    if not server: 
        # p4parser = argparse.ArgumentParser(description='P4Runtime Controller')
        # p4parser.add_argument('--p4info', help='p4info proto in text format from p4c',
        #                     type=str, action="store", required=False,
        #                     default='../simple-version-modify-header.p4.p4info.txt')
        # p4parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
        #                     type=str, action="store", required=False,
        #                     default='../simple-version-modify-header.json')
        # p4args = p4parser.parse_args()

        # if not os.path.exists(args.p4p4info):
        #     p4parser.print_help()
        #     print("\np4info file not found: %s\nHave you run 'make'?" % p4args.p4info)
        #     p4parser.exit(1)
        # if not os.path.exists(args.bmv2_json):
        #     p4parser.print_help()
        #     print("\nBMv2 JSON file not found: %s\nHave you run 'make'?" % p4args.bmv2_json)
        #     p4parser.exit(1)
        p4info_file_path='../simple-version-modify-header.p4.p4info.txt'
        bmv2_file_path='../simple-version-modify-header.json'
        p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)
        s1 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s1',
            address='192.168.56.10:50051',
            device_id=0,
            proto_dump_file='logs/s1-p4runtime-requests.txt')
        s1.MasterArbitrationUpdate()
        s1.SetForwardingPipelineConfig(p4info=p4info_helper.p4info,
                                        bmv2_json_file_path=bmv2_file_path)
        print("Installed P4 Program using SetForwardingPipelineConfig on s1")
    # start to switch info
    #--------------------------------
    if args['use_cm']:
        conn = CM(args['port'], args['server_ip'])
    else:
        conn = SKT(args['port'], args['server_ip'])

    print('-' * 80)
    print(' ' * 25, "Python test for RDMA")

    if server:
        print("Running as server...")
    else:
        print("Running as client...")

    print('-' * 80)

    if args['qp_type'] == IBV_QPT_UD and args['operation_type'] != IBV_WR_SEND:
        print("UD QPs don't support RDMA operations.")
        conn.close()

    conn.handshake()
    # register for QP, GID
    ctx = Context(name=args['ib_dev'])
    pd = PD(ctx)
    cq = CQ(ctx, 100)

    cap = QPCap(max_send_wr=args['tx_depth'], max_recv_wr=args['rx_depth'], max_send_sge=args['sg_depth'],
                max_recv_sge=args['sg_depth'], max_inline_data=args['inline_size'])
    qp_init_attr = QPInitAttr(qp_type=args['qp_type'], scq=cq, rcq=cq, cap=cap, sq_sig_all=True)
    qp = QP(pd, qp_init_attr)

    gid = ctx.query_gid(port_num=1, index=args['gid_index'])
    
    remote_info = conn.handshake(gid=gid, qpn=qp.qp_num)

    gr = GlobalRoute(dgid=remote_info['gid'], sgid_index=args['gid_index'])
    ah_attr = AHAttr(gr=gr, is_global=1, port_num=1)

    if args['qp_type'] == IBV_QPT_UD:
        ah = AH(pd, attr=ah_attr)
        qp.to_rts(QPAttr())
    else:
        qa = QPAttr()
        qa.ah_attr = ah_attr
        qa.dest_qp_num = remote_info['qpn']
        qa.path_mtu = args['mtu']
        qa.max_rd_atomic = 1
        qa.max_dest_rd_atomic = 1
        qa.qp_access_flags = IBV_ACCESS_REMOTE_WRITE | IBV_ACCESS_REMOTE_READ | IBV_ACCESS_LOCAL_WRITE
        if server:
            qp.to_rtr(qa)
        else:
            qp.to_rts(qa)

    conn.handshake()
    if server:
        IOdepth=args['rx_depth']
    else:
        IOdepth=args['tx_depth']
    # register for  
    mr_size = 2*args['size']    #memory safety
    if server:
        if args['qp_type'] == IBV_QPT_UD:   # UD needs more space to store GRH when receiving.
            mr_size = mr_size + GRH_LENGTH
        for i in range(IOdepth):
            content[i] = 'S' * mr_size
    else:
        for i in range(IOdepth):
            content[i] = 'C' * mr_size
    for i in range(IOdepth):
        mr[i]=MR(pd, mr_size, IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE | IBV_ACCESS_REMOTE_READ)
        sgl[i]=[SGE(mr[i].buf, mr[i].length, mr[i].lkey)]
    if args['operation_type'] != IBV_WR_SEND:
        for i in range(IOdepth):
            remote_info[i] = conn.handshake(addr=mr[i].buf, rkey=mr[i].rkey) 
    #when receive rdma request, control message 
 
    if not server:
        while True:
            if offload_flag==True and return_flag==False:
                writeIPRules(p4info_helper,s1,switch_ip_addr,serverC_ip_addr,switch_mac,host_mac,switch_port)
                writeTunnelRules(p4info_helper,s1,remote_info[i]['rkey'], remote_info[i]['addr'])
                # add rewrite rules
            if offload_flag==False and return_flag==True:
                # remove rewrite rules
 
         
            # print(remote_info[i]['rkey'])
            # print(remote_info[i]['addr'])
            # writeTunnelRules(p4info_helper,s1,remote_info[i]['rkey'], remote_info[i]['addr'])
    # wait to adds match-action rule
    # while True:
    #     output = subprocess.check_output(["sudo", "tcpdump", "-i", "eth1", "udp", "and", "src", "host", "192.168.56.3", "and", "dst", "host", "192.168.56.4", "and", "dst", "port", "4791"])
    #     if output:
    #         writeTunnelRules(p4info_helper,s1)
    #         break
    """
    test cast 
    server A: NFS read 
    switch write response to drop, make a copy, check the saved packet 
    
    """


