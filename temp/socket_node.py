# const
import pyverbs.enums as e
# config
from pyverbs.cq import CQ
from pyverbs.qp import QPCap, QPInitAttr, QPAttr, QP
from pyverbs.addr import GID, GlobalRoute, AHAttr
from pyverbs.wr import SGE, SendWR, RecvWR

import src.config.config as c
import src.common.msg as m
# common
from src.common.buffer_attr import BufferAttr, BufferBasic, BufferKey
import src.common.utils as utils
from src.common.file_attr import FileAttr
# pyverbs
from pyverbs.device import Context
from pyverbs.mr import MR
from pyverbs.pd import PD
from src.common.buffer_attr import deserialize, serialize
import pickle
file_dict={"test/test.txt":2,"test/test2.txt":2}


class fileobject:
    def __init__(self,path,host_server=0):
        self.path=str(path)
        self.host_server=host_server
    # def find_server_index(path):
    #     for key,value in file_dict.items():
    #         if key==path:
    #             index=value
    #             return index

class SocketNode:
    def __init__(self, name, options=c.OPTIONS):
        self.name = name
        self.options = options
        self.rdma_ctx = Context(name=self.name)
        self.pd = PD(self.rdma_ctx)
        self.msg_mr = MR(self.pd, c.BUFFER_SIZE,
                         e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        self.read_mr = MR(self.pd, c.BUFFER_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        self.recv_mr = MR(self.pd, c.BUFFER_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        self.file_mr = MR(self.pd, c.FILE_SIZE,
                          e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE)
        # gid
        gid_options = self.options["gid_init"]
        self.gid = self.rdma_ctx.query_gid(gid_options["port_num"], gid_options["gid_index"])
        # cq
        self.cq = self.init_cq()
        # qp
        self.qp = self.init_qp()
        self.buffer_attr,self.buffer_basic_attr,self.buffer_key_attr = self.init_buffer_attr(self.file_mr, c.FILE_SIZE)
        self.remote_metadata = None
        # file attr
        self.file_attr = FileAttr()

    def init_buffer_attr(self, mr: MR, buffer_len=c.BUFFER_SIZE):
        # send the metadata to other
        # return BufferAttr(mr.buf, buffer_len,
        #                   mr.lkey, mr.rkey,
        #                   str(self.gid), self.qp.qp_num)
        return BufferAttr(mr.buf, buffer_len,mr.lkey, mr.rkey,str(self.gid), self.qp.qp_num),BufferBasic(str(self.gid), self.qp.qp_num),BufferKey(mr.buf, buffer_len,mr.lkey,mr.rkey)

    def init_cq(self):
        cqe = self.options["cq_init"]["cqe"]
        cq = CQ(self.rdma_ctx, cqe, None, None, 0)
        cq.req_notify()
        return cq

    def init_qp(self):
        qp_options = self.options["qp_init"]
        cap = QPCap(max_send_wr=qp_options["max_send_wr"], max_recv_wr=qp_options["max_recv_wr"],
                    max_send_sge=qp_options["max_send_sge"], max_recv_sge=qp_options["max_recv_sge"])
        qp_init_attr = QPInitAttr(qp_type=qp_options["qp_type"], qp_context=self.rdma_ctx,
                                  cap=cap, scq=self.cq, rcq=self.cq)
        return QP(self.pd, qp_init_attr)

    def qp2init(self):
        qp_attr = QPAttr(qp_state=e.IBV_QPS_INIT, cur_qp_state=e.IBV_QPS_RESET)
        qp_attr.qp_access_flags = e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE
        self.qp.to_init(qp_attr)
        return self

    def qp2rtr(self, metadata_attr: BufferAttr):
        self.remote_metadata = metadata_attr
        gid_options = self.options["gid_init"]
        qp_attr = QPAttr(qp_state=e.IBV_QPS_RTR, cur_qp_state=e.IBV_QPS_INIT)
        qp_attr.qp_access_flags = e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE
        port_num = gid_options["port_num"]
        remote_gid = GID(metadata_attr.gid)
        gr = GlobalRoute(dgid=remote_gid, sgid_index=gid_options["gid_index"])
        ah_attr = AHAttr(gr=gr, is_global=1, port_num=port_num)
        qp_attr.ah_attr = ah_attr
        qp_attr.dest_qp_num = metadata_attr.qp_num
        self.qp.to_rtr(qp_attr)
        return self

    def qp2rts(self):
        qp_attr = QPAttr(qp_state=e.IBV_QPS_RTS, cur_qp_state=e.IBV_QPS_RTR)
        qp_attr.qp_access_flags = e.IBV_ACCESS_LOCAL_WRITE | e.IBV_ACCESS_REMOTE_READ | e.IBV_ACCESS_REMOTE_WRITE
        # TODO: for bug read test
        qp_attr.timeout = 18
        qp_attr.retry_cnt = 6
        qp_attr.max_rd_atomic = 1
        self.qp.to_rts(qp_attr)
        return self

    # poll cq
    def poll_cq(self, poll_count=1, debug=True):
        self.cq.req_notify()
        npolled = 0
        wc_list = []
        while npolled < poll_count:
            (one_poll_count, wcs) = self.cq.poll(num_entries=poll_count)
            if one_poll_count > 0:
                npolled += one_poll_count
                self.cq.ack_events(one_poll_count)
                if debug:
                    for wc in wcs:
                        # check the wc status, if not success, log the result or die
                        utils.check_wc_status(wc)
                wc_list += wcs
        return wc_list

    def post_write(self, mr: MR, data, length, rkey, remote_addr, opcode=e.IBV_WR_RDMA_WRITE, imm_data=0):
        mr.write(data, length)
        sge = SGE(addr=mr.buf, length=length, lkey=mr.lkey)
        wr = SendWR(opcode=opcode, num_sge=1, sg=[sge, ])
        wr.set_wr_rdma(rkey=rkey, addr=remote_addr)
        if imm_data != 0:
            wr.imm_data = imm_data
        self.qp.post_send(wr)

    # TODO: bug: post read can not poll cq?
    def post_read(self, mr: MR, length, rkey, remote_addr):
        sge = SGE(addr=mr.buf, length=length, lkey=mr.lkey)
        wr = SendWR(opcode=e.IBV_WR_RDMA_READ, num_sge=1, sg=[sge, ])
        wr.set_wr_rdma(rkey=rkey, addr=remote_addr)
        self.qp.post_send(wr)

    def post_send(self, mr: MR, data, length=0):
        if length == 0:
            length = len(data)
        mr.write(data, length)
        sge = SGE(addr=mr.buf, length=length, lkey=mr.lkey)
        wr = SendWR(opcode=e.IBV_WR_SEND, num_sge=1, sg=[sge, ])
        self.qp.post_send(wr)

    def post_recv(self, mr: MR):
        sge = SGE(addr=mr.buf, length=c.BUFFER_SIZE, lkey=mr.lkey)
        wr = RecvWR(num_sge=1, sg=[sge, ])
        self.qp.post_recv(wr)

        
    # initiative push file
    def c_push_file(self, file_path):
        self.post_recv(self.recv_mr)
        self.poll_cq()
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            try:
                self.file_attr.open(file_path)
            except OSError as err:
                err_str = str(err)
                self.post_send(self.msg_mr, err_str)
                return
            # FH+local buffer 
            self.file_attr.file_name = file_path
            # write file name
            self.post_write(self.file_mr, file_path, len(file_path),
                            self.remote_metadata.remote_stag, self.remote_metadata.addr,
                            opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(file_path))
            self.post_recv(self.recv_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode & e.IBV_WC_RECV:
                    msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                    self.post_recv(self.recv_mr)
                    if utils.check_msg(msg, m.FILE_READY_MSG):
                        # send next chunk
                        file_stream = self.file_attr.fd.read(c.FILE_SIZE)
                        size = len(file_stream)
                        self.post_write(self.file_mr, file_stream, size,
                                        self.remote_metadata.remote_stag, self.remote_metadata.addr,
                                        opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=size)
                        print("send next chunk", size)
                    elif utils.check_msg(msg, m.FILE_DONE_MSG):
                        print("file done")
                        # done
                        self.file_attr.done()
            self.file_attr.close()

    # passive save file
    def s_save_file(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        print("send begin")
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                # initiative save file
                size = wc.imm_data
                if size == 0:
                    print("file done")
                    self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                    self.file_attr.done()
                elif self.file_attr.file_name:
                    print("recv file body", size)
                    self.post_recv(self.file_mr)
                    file_stream = self.file_mr.read(size, 0)
                    self.file_attr.fd.write(file_stream)
                    self.post_send(self.msg_mr, m.FILE_READY_MSG)
                else:
                    self.post_recv(self.file_mr)
                    # file_name = self.file_mr.read(size, 0)
                    file_name = "./test/push/des/test.file"  # test
                    self.file_attr.file_name = file_name
                    self.file_attr.fd = utils.create_file(file_name)
                    self.post_send(self.msg_mr, m.FILE_READY_MSG)
            elif wc.opcode & e.IBV_WC_RECV:
                msg = self.file_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_ERR_MSG):
                    break
        if self.file_attr.fd:
            self.post_send(self.msg_mr, m.FILE_DONE_MSG)
            self.poll_cq()
        self.file_attr.close()
#client
    def c_init_send(self,file_path):
        self.file_attr.file_name = file_path
        # self.post_recv(self.recv_mr)
        self.poll_cq()  # post recv
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)

        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            print("send file can begin")
            self.file_attr.fd = utils.create_file(file_path)
            new_file={"path":file_path,"host_server":0}
            # new_file=fileobject(path=str(file_path))
 
            trans_file=pickle.dumps(new_file)
            # self.file_attr.fd = utils.create_file(file_path)
            # loacal_meta= serialize(self.buffer_key_attr)
            
            self.post_send(self.msg_mr, trans_file)
            # self.post_write(self.msg_mr, file_path, len(file_path),
            #                 self.remote_metadata.remote_stag, self.remote_metadata.addr,
            #                 e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(file_path))
            self.post_recv(self.file_mr)
            count=0
            print("wait for server")
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                print("receive opcode= "+str(wc.opcode))
                print(e.IBV_WC_RECV_RDMA_WITH_IMM)
                if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                #if wc.opcode == e.IBV_WR_RDMA_WRITE:
                    file_stream =self.file_mr.read(c.FILE_SIZE,0)
                    #check if client receive file successfully.
                    print("receive file content with size "+str(len(file_stream)))
                    self.file_attr.fd.write(file_stream)
                    count=count+1
                    #re-prepost

                    if wc.imm_data==0:
                        #print("receive total times is "+str(count))
                        self.file_attr.done()
                        self.file_attr.close()
                        break
                    else:
 
                        # self.post_send(self.msg_mr, m.FILE_NEXT_MSG)
                        self.post_recv(self.file_mr)
 
                # if wc.opcode & e.IBV_WC_RECV:
                #     msg = self.file_mr.read(c.FILE_SIZE, 0)
                #     if utils.check_msg(msg, m.FILE_END_MSG):
                #         # print("file done")
                #         # done
                #         self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                #         self.file_attr.done()
                    # print("file done!")
                    # size = wc.imm_data
                    # if size == 0:
                    #     print("file done")
                    #     self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                    #     self.file_attr.done()
                    # else:
                    #     print("recv file body", size)
                    #     self.post_recv(self.file_mr)
                    #     file_stream = self.file_mr.read(size, 0)
                    #     self.file_attr.fd.write(file_stream)
                    #     self.post_send(self.msg_mr, m.FILE_READY_MSG)
                # elif wc.opcode & e.IBV_WC_RECV:
                #     msg = self.file_mr.read(c.BUFFER_SIZE, 0)
                #     if utils.check_msg(msg, m.FILE_ERR_MSG):
                #         print("server file error")
                #         break
            # self.file_attr.close()
        else:
            print("server file error")

    ## p-switch 
    def p_receive_send(self): # proxy-dst, origin proxy server
        #origin server 
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        # print("receive opcode ="+str(wc.opcode))
        # print("this is "+str(self.file_mr))
        # print("use client "+str(c_node.file_mr))
 

        if wc.opcode == e.IBV_WC_RECV:
            # passive push file
            # size = wc.imm_data
            content = self.file_mr.read(c.BUFFER_META_SIZE, 0)
        return content
            # c_node.post_recv(c_node.recv_mr)
            # c_node.post_recv(c_node.file_mr)
            # c_node.post_send(c_node.msg_mr, m.SEND_FILE_MSG)
            # c_node.poll_cq()
            # while not self.file_attr.is_done():
            #     wc = c_node.poll_cq()[0]
            #     print("proxy and server communication")
            #     # if wc.opcode == e.IBV_WR_RDMA_WRITE:
            #     #     file_stream =c_node.file_mr.read(c.FILE_SIZE,0)
            #     #     size = len(file_stream)
            #     #     self.post_write(self.file_mr, file_stream, size,
            #     #             server_meta.remote_stag, server_meta.remote_meta.addr,
            #     #             opcode=e.IBV_WR_RDMA_WRITE)
            #     # self.post_recv(self.recv_mr)
            #     if wc.opcode & e.IBV_WC_RECV:
            #         # self.post_recv(self.recv_mr)
            #         msg = c_node.recv_mr.read(c.BUFFER_SIZE, 0)
            #         if utils.check_msg(msg, m.FILE_BEGIN_MSG):      
            #             c_node.post_write(self.file_mr, remote_data, len(remote_data),
            #             client_meta.server_metadata_attr.remote_stag, client_meta.server_metadata_attr.addr,
            #                 opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(remote_data))
            #         # if utils.check_msg(msg, m.FILE_DONE_MSG):
            #         #     print("file done")
            #         #     # done
            #         #     self.file_attr.done()
                        
            # self.file_attr.close()

    def p_receive_client(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        #print("receive opcode ="+str(wc.opcode))
        
        if wc.opcode == e.IBV_WC_RECV:
            content=self.file_mr.read(c.BUFFER_META_SIZE, 0)
        return content 
    def send_for_meta(self,content):
 
        self.poll_cq()  # post recv
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            self.post_recv(self.file_mr)
            self.post_send(self.msg_mr,content)
            self.poll_cq()  # post send
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]  # post recv
                if wc.opcode == e.IBV_WC_RECV:
                    new_content=self.file_mr.read(c.BUFFER_META_SIZE, 0)
                    #print(pickle.loads(new_content))
                    self.file_attr.done()
        # new_file=pickle.loads(new_content)
        ##switch knows choose which server 
        return new_content
    def send_for_file(self,content):
        file_stream_pool=[]
        self.poll_cq()  # post recv
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            self.post_recv(self.file_mr)
            self.post_send(self.msg_mr,content)
            # self.poll_cq() 
            count=0
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
 
                if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                   # print("## receive file!")
                    file_stream= self.file_mr.read(c.FILE_SIZE, 0)
                    #print("receive file stream with size "+str(len(file_stream)))
                    size = wc.imm_data
                    if size!=0:
                        if c.is_control_plane==True:
                            file_stream_pool.append(file_stream)
                        self.post_recv(self.file_mr)
                        self.post_send(self.msg_mr, m.FILE_NEXT_MSG) 
                    #repost 
                    # count=count+1
                    # if count<2:
                    #     self.post_recv(self.file_mr)
                    #     self.post_send(self.msg_mr, m.FILE_NEXT_MSG)
                    #     self.poll_cq()
                    # else:
                    #     print("file done ")
                    #     self.file_attr.done()
 
                    #     self.post_send(self.msg_mr, m.FILE_NEXT_MSG)
                    #     self.poll_cq()
 
                    # self.poll_cq()
                        
                # if utils.check_msg(self.file_mr.read(c.FILE_SIZE, 0), m.FILE_END_MSG):
                #     # print("receive server's response!")
 
                #     print("file done")
                #     # done
                #     self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                #     self.file_attr.done()
                # if wc.opcode & e.IBV_WC_RECV:
                #     # print(wc.opcode)
                     
                #     msg = self.file_mr.read(c.FILE_SIZE, 0)
                #     self.post_recv(self.file_mr)
                #     # print(msg.decode("UTF-8", "ignore").strip("\x00").encode())
                #     if utils.check_msg(msg,  m.FILE_END_MSG):
                    else:
                        # self.post_send(self.msg_mr, m.FILE_DONE_MSG)

                        #print("file end msg!")
                        self.file_attr.done()



            return file_stream_pool    


    def p_trans_write(self,server_metda,content):
        self.poll_cq()  # post recv
        file_stream_pool=[]
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            self.post_send(self.msg_mr, content)
            # self.post_write(self.file_mr, content, len(content),
            #             server_metda.remote_stag, server_metda.addr,
            #                 opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=10)
            # print("switch sends to server")
         
        #change from file stream to file stream pool 
        if c.is_control_plane==False:
            print("wait for host node return to client..")
            return 
        else:
            self.post_recv(self.file_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                    print("## receive file!")
                    file_stream= self.file_mr.read(c.FILE_SIZE, 0)
                    print("receive file stream with size "+str(len(file_stream)))
                    size = wc.imm_data
                    if size!=0:
                        file_stream_pool.append(file_stream)
                        self.post_recv(self.file_mr)
                        self.post_send(self.msg_mr, m.FILE_NEXT_MSG) 
                    else:
                            # self.post_send(self.msg_mr, m.FILE_DONE_MSG)

                        print("file end msg!")
                        self.file_attr.done()
                # self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                # file_stream= self.file_mr.read(c.BUFFER_META_SIZE, 0)
 
                # # print("receive server's response!")
                # self.file_attr.done()
        # return file_stream_pool
    def p_return_write(self,file_stream_pool,client_meta):
        # self.post_write(self.file_mr, file_stream, len(file_stream),
        #                 client_meta.remote_stag, client_meta.addr,
        #                     opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=10)
        # print("return content to client")
        # self.post_recv(self.recv_mr)
        # while not self.file_attr.is_done():
        #     wc = self.poll_cq()[0]
    
        #     if wc.opcode & e.IBV_WC_RECV:
        #         msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        #         if utils.check_msg(msg, m.FILE_DONE_MSG): 
        #             # print("switch function completes!")
        #             self.file_attr.done()
        self.post_recv(self.recv_mr)
        for file_stream in range(len(file_stream_pool)):
            #todo: update pre-post in client 
            if file_stream<len(file_stream_pool)-1:
                imm=10
            else:
                imm=0
            self.post_write(self.file_mr, file_stream_pool[file_stream], len(file_stream_pool[file_stream]),
                            client_meta.remote_stag, client_meta.addr,
                                opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=imm)
            #last one do not need client's signal
            if file_stream<len(file_stream_pool)-1:
                flag=False
                while flag==False:
                    wc = self.poll_cq()[0]
                    if wc.opcode & e.IBV_WC_RECV:
                    # self.post_recv(self.recv_mr)
                        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                        if utils.check_msg(msg, m.FILE_NEXT_MSG):
                            flag=True
                            self.post_recv(self.recv_mr)
                    
             
        print("return content to client")

    def s_receive_send(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        if wc.opcode == e.IBV_WC_SEND:
            # passive push file
            # size = wc.imm_data
            file_name=c.FILE_NAME
            print(remote_meta)
            remote_meta = deserialize(self.file_mr.read(c.BUFFER_META_SIZE, 0))
            try:
                self.file_attr.open(file_name)
            except OSError as err:
                self.post_send(self.msg_mr, m.FILE_ERR_MSG)
                return
            self.file_attr.file_name = file_name
            file_stream = self.file_attr.fd.read(c.FILE_SIZE)
            size = len(file_stream)
            #def post_write(self, mr: MR, data, length, rkey, remote_addr, opcode=e.IBV_WR_RDMA_WRITE, imm_data=0)
            self.post_write(self.file_mr, file_stream, size,
                            remote_meta.rkey, remote_meta.addr,
                            opcode=e.IBV_WR_RDMA_WRITE)
        self.post_recv(self.recv_mr)
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode & e.IBV_WC_RECV:
                self.post_recv(self.recv_mr)
                msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_DONE_MSG):
                    print("file done")
                    # done
                    self.file_attr.done()
        self.file_attr.close()
        '''
        file mr 用msg mr send 出去
        self.post_recv(self.file_mr)
        msg替换为file mr metadata 
        self.post_send(file metadata)
        check file msg opcode:
        done 
    def p_receive_send(self):
        self.post_recv(msg_mr)
        check msg_mr opcode=send
        self.post_recv(file_mr)
        self.post_send(file metadata)
        check file msg opcode:
        write to c file mr
    def s_receive_send(self):
        self.post_recv(msg_mr)
        read file content to file_mr
        write(file_mr to p.file_mr)

    '''
    def s_receive_meta_send(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
          # post recv
 
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode == e.IBV_WC_RECV:
            # passive push file
            # size = wc.imm_data
                remote_file = pickle.loads(self.file_mr.read(c.BUFFER_META_SIZE, 0))
                remote_file["host_server"]=2
                new_content=pickle.dumps(remote_file)
                self.post_send(self.msg_mr, new_content)
                self.file_attr.done()
    def s_receive_file_send(self,client_metda):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        if wc.opcode == e.IBV_WC_RECV:
            # passive push file
            # size = wc.imm_data
            # print("begin return to switch")
            # file_name=c.FILE_NAME
            file_object = pickle.loads(self.file_mr.read(c.BUFFER_META_SIZE, 0))
            file_name=file_object["path"]
            file_name=str(file_name)
            print(file_name)
            try:
                self.file_attr.open(file_name)
            except OSError as err:
                self.post_send(self.msg_mr, m.FILE_ERR_MSG)
                return
            self.file_attr.file_name = file_name
            ##per read limited to file_size
            self.post_recv(self.recv_mr)
            while True:
                dc =  self.file_attr.fd.read(c.FILE_SIZE)
                if len(dc) == 0: 
 
                    #print("return file ends!")
                    self.post_write(self.file_mr, dc, len(dc),
                    client_metda.remote_stag, client_metda.addr,
                    opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=0)
                    # self.post_send(self.msg_mr, m.FILE_END_MSG)
                    
                    # self.poll_cq()
                    print("end signal ok!")
                    self.file_attr.done()
                    break  
                else:
                    print("## return file with size "+str(len(dc)))
 
                    self.post_write(self.file_mr, dc, len(dc),
                    client_metda.remote_stag, client_metda.addr,
                    opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=10)
                    # until switch receives the write message 
                    if c.is_pause_time==True:
                        time.sleep(1)
                    else:
                        flag=False
                        while flag==False:
                            wc = self.poll_cq()[0]
                            if wc.opcode & e.IBV_WC_RECV:
                            # self.post_recv(self.recv_mr)
                                msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                                if utils.check_msg(msg, m.FILE_NEXT_MSG):
                                    flag=True
                                    self.post_recv(self.recv_mr)

 
            #print("file size is "+str(size))
            #def post_write(self, mr: MR, data, length, rkey, remote_addr, opcode=e.IBV_WR_RDMA_WRITE, imm_data=0)
            ##todo:  
 
 
            # print("write to client")
            # self.file_attr.done()

            # print("wait for done message...")
            # while not self.file_attr.is_done():
            #     wc = self.poll_cq()[0]
            #     # print(wc.opcode)
            #     if wc.opcode & e.IBV_WC_RECV:
            #         # self.post_recv(self.recv_mr)
            #         msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
            #         self.post_recv(self.recv_mr)
            #         if utils.check_msg(msg, m.FILE_DONE_MSG):
            #             print("file done")
            #             # done
            #             self.file_attr.done()
            #         else:
            #             print("no file done!")

        self.file_attr.close()
    def c_pull_file(self, file_path):
        self.file_attr.file_name = file_path
        # self.post_recv(self.recv_mr)
        self.poll_cq()  # post recv
        msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
        if utils.check_msg(msg, m.FILE_BEGIN_MSG):
            self.file_attr.fd = utils.create_file("./test/pull/src/pull.txt")
            # self.file_attr.fd = utils.create_file(file_path)
            self.post_write(self.msg_mr, file_path, len(file_path),
                            self.remote_metadata.remote_stag, self.remote_metadata.addr,
                            e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=len(file_path))
            self.post_recv(self.file_mr)
            while not self.file_attr.is_done():
                wc = self.poll_cq()[0]
                if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
                    size = wc.imm_data
                    if size == 0:
                        print("file done")
                        self.post_send(self.msg_mr, m.FILE_DONE_MSG)
                        self.file_attr.done()
                    else:
                        print("recv file body", size)
                        self.post_recv(self.file_mr)
                        file_stream = self.file_mr.read(size, 0)
                        self.file_attr.fd.write(file_stream)
                        self.post_send(self.msg_mr, m.FILE_READY_MSG)
                elif wc.opcode & e.IBV_WC_RECV:
                    msg = self.file_mr.read(c.BUFFER_SIZE, 0)
                    if utils.check_msg(msg, m.FILE_ERR_MSG):
                        print("server file error")
                        break
            self.file_attr.close()
        else:
            print("server file error")

    def s_push_file(self):
        self.post_recv(self.file_mr)
        self.post_send(self.msg_mr, m.FILE_BEGIN_MSG)
        self.poll_cq()  # post send
        wc = self.poll_cq()[0]  # post recv
        if wc.opcode == e.IBV_WC_RECV_RDMA_WITH_IMM:
            # passive push file
            size = wc.imm_data
            file_name = self.file_mr.read(size, 0)
            try:
                self.file_attr.open(file_name)
            except OSError as err:
                self.post_send(self.msg_mr, m.FILE_ERR_MSG)
                return
            self.file_attr.file_name = file_name
            file_stream = self.file_attr.fd.read(c.FILE_SIZE)
            size = len(file_stream)
            self.post_write(self.file_mr, file_stream, size,
                            self.remote_metadata.remote_stag, self.remote_metadata.addr,
                            opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=size)
        self.post_recv(self.recv_mr)
        while not self.file_attr.is_done():
            wc = self.poll_cq()[0]
            if wc.opcode & e.IBV_WC_RECV:
                self.post_recv(self.recv_mr)
                msg = self.recv_mr.read(c.BUFFER_SIZE, 0)
                if utils.check_msg(msg, m.FILE_READY_MSG):
                    # send next chunk
                    file_stream = self.file_attr.fd.read(c.FILE_SIZE)
                    size = len(file_stream)
                    self.post_write(self.file_mr, file_stream, size,
                                    self.remote_metadata.remote_stag, self.remote_metadata.addr,
                                    opcode=e.IBV_WR_RDMA_WRITE_WITH_IMM, imm_data=size)
                elif utils.check_msg(msg, m.FILE_DONE_MSG):
                    print("file done")
                    # done
                    self.file_attr.done()
        self.file_attr.close()

    def close(self):
        self.rdma_ctx.close()
        self.pd.close()
        self.msg_mr.close()
        self.recv_mr.close()
        self.file_mr.close()
        self.read_mr.close()
        self.cq.close()
        self.qp.close()
        self.file_attr.close()
