
from scapy.all import *
from scapy.contrib.rdma import *

 
class RDMASegment(Packet):
    name = "RDMA Segment"
    fields_desc = [
        ByteField("opcode", 0),
        ByteField("flags", 0),
        XIntField("length", 0),
        ConditionalField(StrLenField("data", "", length_from=lambda pkt: pkt.length), lambda pkt:pkt.length > 0)
    ]

# 定义RPC over RDMA协议的Write Chunk和Read Chunk层级字段
class WriteChunk(Packet):
    name = "Write Chunk"
    fields_desc = [
        ByteField("count", 0),
        PacketListField("rdma_segments", [], RDMASegment, length_from=lambda pkt: pkt.count)
    ]

class ReadChunk(Packet):
    name = "Read Chunk"
    fields_desc = [
        ByteField("count", 0),
        PacketListField("rdma_segments", [], RDMASegment, length_from=lambda pkt: pkt.count)
    ]

# 定义RPC over RDMA协议的Write列表和Read列表层级字段
class WriteList(Packet):
    name = "Write List"
    fields_desc = [
        ByteField("count", 0),
        PacketListField("write_chunks", [], WriteChunk, length_from=lambda pkt: pkt.count)
    ]

class ReadList(Packet):
    name = "Read List"
    fields_desc = [
        ByteField("count", 0),
        PacketListField("read_chunks", [], ReadChunk, length_from=lambda pkt: pkt.count)
    ]

# 定义RPC over RDMA协议的层级字段
class RPConRDMA(Packet):
    name = "RPC over RDMA"
    fields_desc = [
        XShortField("xid", 0),
        ByteField("rtype", 0),
        ByteField("rpc_version", 0),
        XLongField("prog", 0),
        XLongField("vers", 0),
        XLongField("proc", 0),
        PacketListField("write_list", [], WriteList, count_from=lambda pkt:pkt.rtype & 0x10 != 0),
        PacketListField("read_list", [], ReadList, count_from=lambda pkt:pkt.rtype & 0x08 != 0)
    ]

# 从文件中读取RPC over RDMA报文
packets = rdma_load('rpc_over_rdma.pcap')

# 解析报文并提取信息
for packet in packets:
    rpc_over_rdma = packet[RPConRDMA]
    
    print("XID: ", rpc_over_rdma.xid)
    print("RPC Type: ", rpc_over_rdma.rtype)
    print("RPC Version: ", rpc_over_rdma.rpc_version)
    print("Program Number: ", rpc_over_rdma.prog)
    print("Version Number: ", rpc_over_rdma.vers)
    print("Procedure Number: ", rpc_over_rdma.proc)
    
    # 解析Write列表
    if rpc_over_rdma.write_list:
        write_list = rpc_over_rdma.write_list[0]  # 只解析第一个Write列表
        print("\nWrite List:")
        print("Count: ", write_list.count)
        
        # 解析Write Chunk
        for write_chunk in write_list.write_chunks:
            print("\nWrite Chunk Count: ", write_chunk.count)
            
            # 解析RDM A Segment
            for rdma_segment in write_chunk.rdma_segments:
                print("RDM A Segment Opcode: ", rdma_segment.opcode)
                print("RDM A Segment Flags: ", rdma_segment.flags)
                print("RDM A Segment Length: ", rdma_segment.length)
                print("RDM A Segment Data: ", rdma_segment.data)
    
    # 解析Read列表
    if rpc_over_rdma.read_list:
        read_list = rpc_over_rdma.read_list[0]  # 只解析第一个Read列表
        print("\nRead List:")
        print("Count: ", read_list.count)
        
        # 解析Read Chunk
        for read_chunk in read_list.r
