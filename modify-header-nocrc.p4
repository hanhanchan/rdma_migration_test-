/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/
typedef bit<16> ether_type_t;
typedef bit<8> ip_protocol_t;

const ether_type_t ETHERTYPE_IPV4 = 16w0x0800;
const ip_protocol_t IP_PROTOCOLS_UDP = 0x11;
const bit<16> UDP_ROCE_V2 = 4791;

header ethernet_h {
    bit<48>   dst_addr;
    bit<48>   src_addr;
    bit<16>   ether_type;
}

header ipv4_h {
    bit<4>   version;
    bit<4>   ihl;
    bit<8>   diffserv;
    bit<16>  total_len;
    bit<16>  identification;
    bit<3>   flags;
    bit<13>  frag_offset;
    bit<8>   ttl;
    bit<8>   protocol;
    bit<16>  hdr_checksum;
    bit<32>  src_addr;
    bit<32>  dst_addr;
}

header udp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<16> udp_total_len;
    bit<16> checksum;
}

header ib_bth_h {
    bit<8>  opcode; // 00001010 RC RDMA Write, 00101010 UC RDMA Write, 00000100 RC SEND
    bit<8>  flags;  // 1 bit solicited event, 1 bit migreq, 2 bit padcount, 4 bit headerversion
    bit<16> partition_key;
    bit<8>  reserved0;
    bit<24> destination_qp;
    bit<1>  ack_request; 
    bit<7>  reserved1;   
    bit<24> packet_seqnum;
}

header ib_reth_h {
    bit<64> virtual_addr;
    bit<32> remote_key;
    bit<32> dma_length;
}
struct my_ingress_headers_t {
    ethernet_h      ethernet;
    ipv4_h          ipv4;
    udp_h           udp;
    ib_bth_h        bth;
    ib_reth_h       reth;
}
struct my_ingress_metadata_t {
}
/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in pkt,
                out my_ingress_headers_t hdr,
                out my_ingress_metadata_t meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4 : parse_ipv4;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            IP_PROTOCOLS_UDP : parse_udp;
        }
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition select(hdr.udp.dst_port) {
            UDP_ROCE_V2 : parse_bth;
        }
    }

    state parse_bth {
        pkt.extract(hdr.bth);
        transition select(hdr.bth.opcode) {
            0x00001010 : parse_reth;
            0x00101010 : parse_reth;
            default  : accept;
        }
    }

    state parse_reth {
        pkt.extract(hdr.reth);
        transition accept;
    }
                
}

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(out my_ingress_headers_t hdr, out my_ingress_metadata_t meta,) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action multicast() {
        standard_metadata.mcast_grp = 1;
    }

    action mac_forward(egressSpec_t port) {
        standard_metadata.egress_spec = port;
    }

    table ip_lookup {
        key = {
            hdr.ipv4.dst_addr : exact;
        }
        actions = {
            multicast;
            mac_forward;
            drop;
        }
        size = 1024;
        default_action = multicast;
    }
    apply {
        if (hdr.ipv4.isValid())
            ip_lookup.apply();
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
   // todo: discriminate send/write 
   // for write first 
   action translate(bit<24> qp, bit<64> virtual_addr, bit<32> remote_key) {
        hdr.bth.destination_qp = qp;
        hdr.reth.remote_key = remote_key;
        hdr.reth.virtual_addr = virtual_addr;
    }

    table rdma_translate {
        key = {
            hdr.ipv4.dst_addr       : exact;
            hdr.reth.isValid()      : exact;
            hdr.bth.destination_qp  : exact;
        }
        actions = {
            translate;
            NoAction;
        }
        size = 512;
    }

    action swap(bit<32> dst_addr) {
        hdr.ipv4.dst_addr = dst_addr;
    }

    table swap_dst_ip {
        key = {
           eg_intr_md.egress_port : exact; 
        }
        actions = {
            swap;
        }
        size = 512;
    }
    action drop() {
        mark_to_drop(standard_metadata);
    }

    apply {
        // Prune multicast packet to ingress port to preventing loop
        if (standard_metadata.egress_port == standard_metadata.ingress_port)
            drop();
        if(rdma_translate.apply().hit) {
            swap_dst_ip.apply();
        }
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {

    }
}


/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out pkt, inout headers hdr) {
    apply {
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.udp);
        pkt.emit(hdr.bth);
        pkt.emit(hdr.reth);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
