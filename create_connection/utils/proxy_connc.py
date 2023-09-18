#!/usr/bin/python3.8
import sys

sys.path.append('..')

from utils.connection import SKT, CM
from utils.param_parser import parser

from pyverbs.addr import AH, AHAttr, GlobalRoute
from pyverbs.cq import CQ
from pyverbs.device import Context
from pyverbs.enums import *
from pyverbs.mr import MR
from pyverbs.pd import PD
from pyverbs.qp import QP, QPCap, QPInitAttr, QPAttr
from pyverbs.wr import SGE, RecvWR, SendWR
#types in https://github.com/linux-rdma/rdma-core/tree/master/libibverbs/man, 此目录下找


RECV_WR = 1
SEND_WR = 2
GRH_LENGTH = 40
# content=["content1","content2","content3","content4"]
# mr=["mr1","mr2","mr3","mr4"]
# sgl=["sgl1","sgl2","sgl3","sgl4"]
# remote_info=["remote_info1","remote_info2","remote_info3","remote_info4"]
# wr=["wr1","wr2","wr3","wr4"]
# TODO: Error handling
def read_mr(mr):
    if args['qp_type'] == IBV_QPT_UD and server:
        return mr.read(mr.length - GRH_LENGTH, GRH_LENGTH).decode()
    else:
        return mr.read(mr.length, 0).decode()   

args = parser.parse_args()

server = not bool(args['server_ip'])
dst = not bool(args['dst_ip'])
if args['use_cm']:
    conn = CM(args['port'], args['server_ip'])
    connc_numbers=1
    if  proxy: 
        conn1 = CM(args['port'], args['dst_ip'])
        connc_numbers=connc_numbers+1

else:
    conn = SKT(args['port'], args['server_ip'])
    if  proxy:
        conn1 = SKT(args['port'], args['dst_ip'])
        connc_numbers=connc_numbers+1

print('-' * 80)
print(' ' * 25, "Python test for RDMA")

if server:
    if dst:
        print("Running as proxy...")
    else:
        server_file_list=[]
        print("Running as dst...")
        
else:
    client_file_list=[]
    print("Running as client...")

print('-' * 80)
def decimal_to_binary(decimal_num):
    while decimal_num > 0:
        remainder = decimal_num % 2
        binary_num = str(remainder) + binary_num
        decimal_num = decimal_num // 2
    return binary_num


# if args['qp_type'] == IBV_QPT_UD and args['operation_type'] != IBV_WR_SEND:
#     print("UD QPs don't support RDMA operations.")
#     conn.close()

# conn.handshake

# register for QP, GID
# register for, while proxy need to 
mr_size = args['file_size']+500   #memory safety
 
if server:
    job_numbers=args['rx_depth']
else:
    job_numbers=args['tx_depth']
class Create_QP_Connection(self,conn):
    self.ctx = Context(name=args['ib_dev'])
    self.pd = PD(ctx)
    self.cq = CQ(ctx, 100)

    self.cap = QPCap(max_send_wr=args['tx_depth'], max_recv_wr=args['rx_depth'], max_send_sge=args['sg_depth'],
                max_recv_sge=args['sg_depth'], max_inline_data=args['inline_size'])
    self.qp_init_attr = QPInitAttr(qp_type=args['qp_type'], scq=cq, rcq=cq, cap=cap, sq_sig_all=True)
    self.qp = QP(self.pd, self.qp_init_attr)

    self.gid = self.ctx.query_gid(port_num=1, index=args['gid_index'])    
    self.remote_info = conn.handshake(gid=self.gid, qpn=self.qp.qp_num)
    self.mr_list=[]
    self.sgl_list=[]
    def Change_QP_state(self):
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
    def Create_MR_region(self):
        mr=MR(pd, mr_size, IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE | IBV_ACCESS_REMOTE_READ)
        sgl=SGE(mr.buf, mr.length, mr.lkey)
        self.mr_list.append(mr)
        self.sgl_list.append(sgl)
    def Change_recv_state(self):
        for i,j in zip(self.mr_list,self.sgl_list):
            i = RecvWR(RECV_WR, len(j), j)
            self.qp.post_recv(i)

if not proxy:
    init_connc=Create_QP_Connection(conn)
    init_connc.Change_QP_state()
    for i in range(job_numbers):
        init_connc.Create_MR_region()
    if server:
        init_connc.Change_recv_state()
else:
    init_client_proxy=Create_QP_Connection(conn)
    init_proxy_host= Create_QP_Connection(conn1)
    init_client_proxy.Change_QP_state()
    init_proxy_host.Change_QP_state()
    for i in range(job_numbers):
        init_client_proxy.Create_MR_region()
        init_proxy_host.Create_MR_region()
    init_client_proxy.Change_recv_state()
# create file process  --file_size

if proxy:
    pass
else:
    if(args["test_mode"]=="write"):
        if server:
            #todo: create file bash 
            for i in range(job_numbers):
                server_file_list.append("test{i}.txt")
                server=decimal_to_binary(i)
                server_index.append(index)
            for i in range(job_numbers):
                fr=open(server_file_list[i],mode="r")
                fr_content=str(decimal_to_binary(i))
                fr_content=fr_content+str(fr.read())
                fr.close()         
        else:
            for i in range(job_numbers):
                client_file_list.append("test{i}.txt")
                index=decimal_to_binary(i)
                file_index.append(index)            
            for i in range(job_numbers):
                fr=open(client_file_list[i],mode="w")
                fr_content=str(decimal_to_binary(i))
                

                fr.close()


for i in range(IOdepth):
    content.append("content{i}")
    mr.append("mr{i}")
    sgl.append("sgl{i}")
    remote.append("remote{i}") #与之前的remote info不同
    wr.append("wr{i}")
 
# register for, while proxy need to 
mr_size = args['file_size']+500   #memory safety
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


"""
workflow 
# client send_only to server 
# 如何实现proxy 收到send only后再转发到server 
# proxy收到file后再create?
"""

#发包顺序




if args['operation_type'] != IBV_WR_SEND:
    for i in range(IOdepth):
        remote_info[i] = conn.handshake(addr=mr[i].buf, rkey=mr[i].rkey) 

# exchange begins
if not server and not proxy: #client








for i in range(args['iters']):
    print("Iter: " + f"{i + 1}/{args['iters']}")
    for i in range(IOdepth):
        mr[i].write(content[i], len(content[i]))
        print("MR Content before test:" + read_mr(mr[i]))
    if server and args['operation_type'] == IBV_WR_SEND:
        for i in range(IOdepth):
            wr[i] = RecvWR(RECV_WR, len(sgl[i]), sgl)
            qp.post_recv(wr[i])

    conn.handshake()
    #required for send only 
    if not server:
        for i in range(IOdepth):
            wr[i]=SendWR(2, opcode=args['operation_type'], num_sge=1, sg=sgl[i])
            if args['qp_type'] == IBV_QPT_UD:
                wr[i].set_wr_ud(ah, remote_info['qpn'], 0)
            elif args['operation_type'] != IBV_WR_SEND:
                wr[i].set_wr_rdma(remote_info[i]['rkey'], remote_info[i]['addr'])
            qp.post_send(wr[i])

    conn.handshake()

    if not server or args['operation_type'] == IBV_WR_SEND:
        wc_num, wc_list = cq.poll()
    for i in range(IOdepth):
        print("MR" + str(i)+"Content after test:" + read_mr(mr[i]))
conn.handshake()
conn.close()

print('-' * 80)


#if socket.recv 收到数据
'''
以NFS read为例
client:
1.open file 
2.cMR 
3.basic info with proxy
4.send (fileindex+cMR)  +handshake 
5.socket.recv(ok) 任务完成

proxy:与两连接分别都开一段MR  
1. MR to post recv 1
2. post recv 2 
3. socket.recv(send) pack new packet
4. send to server + handshake
5. recv2(write)
6. pack write to client + send ok


server: 
1. post recv 
2. recv(send) pack new
3. write to proxy.recv 2 +handshake 
4. 

 
'''