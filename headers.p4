
#ifndef _HEADERS_
#define _HEADERS_

#include "types.p4"

 
header ethernet_h {
    mac_addr_t mst_addr;
    mac_addr_t msrc_addr;
    bit<16>    ether_type;
}

header ipv4_h {
    bit<4>        version;
    bit<4>        ihl;
    bit<8>        diffserv;
    bit<16>       total_len;
    bit<16>       identification;
    bit<3>        flags;
    bit<13>       frag_offset;
    bit<8>        ttl;
    ip_protocol_t protocol;
    bit<16>       hdr_checksum;
    ipv4_addr_t   src_addr;
    ipv4_addr_t   dst_addr;
}
 
header udp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> length;
    bit<16> checksum;
}
 
// InfiniBand-RoCE Base Transport Header
header ib_bth_h {
    ib_opcode_t       opcode;
    bit<1>            se;
    bit<1>            migration_req;
    bit<2>            pad_count;
    bit<4>            transport_version;
    bit<16>           partition_key;
    bit<1>            f_res1;
    bit<1>            b_res1;
    bit<6>            reserved;
    queue_pair_t      dst_qp;
    bit<1>            ack_req;
    bit<7>            reserved2;
    sequence_number_t psn;
}

 

// InfiniBand-RoCE RDMA Extended Transport Header
header ib_reth_h {
    bit<64> addr;
    bit<32> r_key;
    bit<32> len;
}

// InfiniBand-RoCE Immediate Header
header ib_immediate_h {
    bit<32> immediate;
}

// InfiniBand-RoCE ICRC Header
header ib_icrc_h {
    bit<32> icrc;
}

 
typedef bit<32> program_t;
typedef bit<2> rver_t;
typedef bit<2> programv_t;
typedef bit<1> ver_t;
 


header rpc_rdma_h{
    bit<32> xid;
    ver_t ver;
    flow_ctrl_t flow_ctrl;
    rpc_rdma_type_t rmsg_type;   
}

header reply_chunk1_h{
    rhandle_t rhandle;
    dma_len_t dma_len;
    roffset_t roffset;
}
header reply_chunk2_h{
    rhandle_t rhandle;
    dma_len_t dma_len;
    roffset_t roffset;
}

header rpc_h{
    xid_t xid;
    mtye_t mtype;
    rver_t rver;
    program_t program;
    programv_t programv;
    rpc_type_t rproc;
}
// Full header stack
struct my_ingress_headers_t {
    ethernet_h     ethernet;
    ipv4_h         ipv4;
    udp_h          udp;
    ib_bth_h       ib_bth;
    ib_reth_h      ib_reth;
    ib_immediate_h ib_immediate;
    ib_icrc_h      ib_icrc;
    rpc_h          rpc;
    reply_chunk1_h reply_chunk1;
    reply_chunk2_h  reply_chunk2;
    rpc_rdma_h     rpc_rdma;
  
}
struct my_ingress_metadata_t {
}
#endif /* _HEADERS_ */
