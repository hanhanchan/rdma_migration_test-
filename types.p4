
#ifndef _TYPES_
#define _TYPES_

#include "configuration.p4"
typedef bit<16> ether_type_t;
typedef bit<48> mac_addr_t;
typedef bit<8> ip_protocol_t;
typedef bit<32> ipv4_addr_t;
typedef bit<16> udp_port_t;
typedef bit<3> max_concurrent_t;
typedef bit<3> max_reply_chunk_t;
typedef bit<2> rver_t;
typedef bit<1> mtye_t;
typedef bit<32> program_t;
typedef bit<2> rver_t;
typedef bit<2> programv_t;
typedef bit<1> ver_t;
typedef bit<8> flow_ctrl_t;
typedef bit<4> server_offload_t;
typedef bit<32> xid_t;
const ip_protocol_t IP_PROTOCOLS_UDP = 0x11;
const ether_type_t ETHERTYPE_IPV4   = 16w0x0800;
const ether_type_t ETHERTYPE_ARP    = 16w0x0806;
const ether_type_t ETHERTYPE_ROCEv1 = 16w0x8915;
const udp_port_t UDP_PORT_ROCEV2        =   4791;
typedef bit<16> rhandle_t;
typedef bit<8> dma_len_t;
typedef bit<64> roffset_t;
enum bit<8> ip_protocol_t {
    ICMP = 1,
    UDP  = 17
}

// for ib 
// IB/RoCE-specific types:
typedef bit<128> ib_gid_t;
typedef bit<24> sequence_number_t;
typedef bit<24> queue_pair_t;
typedef bit<32> rkey_t;
typedef bit<64> addr_t;

// UC opcodes
enum bit<8> ib_opcode_t {
    UC_SEND_FIRST                = 8w0b00100000,
    UC_SEND_MIDDLE               = 8w0b00100001,
    UC_SEND_LAST                 = 8w0b00100010,
    UC_SEND_LAST_IMMEDIATE       = 8w0b00100011,
    UC_SEND_ONLY                 = 8w0b00100100,
    UC_SEND_ONLY_IMMEDIATE       = 8w0b00100101,
    UC_RDMA_WRITE_FIRST          = 8w0b00100110,
    UC_RDMA_WRITE_MIDDLE         = 8w0b00100111,
    UC_RDMA_WRITE_LAST           = 8w0b00101000,
    UC_RDMA_WRITE_LAST_IMMEDIATE = 8w0b00101001,
    UC_RDMA_WRITE_ONLY           = 8w0b00101010,
    UC_RDMA_WRITE_ONLY_IMMEDIATE = 8w0b00101011,
    RC_SEND_FIRST                = 8w0b00000000,
    RC_SEND_MIDDLE               = 8w0b00000001,   
    RC_SEND_LAST                 = 8w0b00000010,
    RC_SEND_LAST_IMMEDIATE       = 8w0b00000011,
    RC_SEND_ONLY                 = 8w0b00000100,
    RC_SEND_ONLY_IMMEDIATE       = 8w0b00000101,
    RC_RDMA_WRITE_FIRST          = 8w0b00000110,
    RC_RDMA_WRITE_MIDDLE         = 8w0b00000111,
    RC_RDMA_WRITE_LAST           = 8w0b00001000,
    RC_RDMA_WRITE_LAST_IMMEDIATE = 8w0b00001001,
    RC_RDMA_WRITE_ONLY           = 8w0b00001010,
    RC_RDMA_WRITE_ONLY_IMMEDIATE = 8w0b00001011,
}
//rpc related type
const ver_t RPC_RDMA_VERSION=1
const flow_ctrl_t RPC_FLOW_CONTROL=128 
enum bit<2> rpc_rdma_type_t {
    RDMA_MSG = 0,
    RDMA_NOMSG = 1 
}

const mtye_t MSG_TYPE=0 //call 
const rver_t RPC_VERSION=2
const program_t RPC_PROGRAM=100003
const programv_t RPC_PROGRAMV=3

enum bit<8> rpc_type_t {
    // todo: remedy other procedure type 
    void=0 ,
    GETATTR=1 ,
    ACCESS=4 ,
    READDIRPLUS=17
}
 
// RDMA MTU (packet size). Matches ibv_mtu enum in verbs.h
enum bit<3> packet_size_t {
    IBV_MTU_128  = 0, // not actually defined in IB, but useful for no recirculation tests
    IBV_MTU_256  = 1,
    IBV_MTU_512  = 2,
    IBV_MTU_1024 = 3
}

// Drop probability between 0 and 32767
typedef bit<16> drop_probability_t;

 
// Port metadata, used for drop simulation
struct port_metadata_t {
    drop_probability_t ingress_drop_probability;
    drop_probability_t egress_drop_probability;
}

#endif /* _TYPES_ */
