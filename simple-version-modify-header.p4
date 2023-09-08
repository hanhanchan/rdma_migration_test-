/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>
#include "headers.p4"

//time1121
parser MyParser(packet_in pkt,
                out headers hdr,
                inout metadata meta,
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
            UDP_PORT_ROCEV2 : parse_bth;
        }
    }
    state parse_bth {
        pkt.extract(hdr.ib_bth);
        transition select(hdr.ib_bth.opcode) {
            default: parse_reth;
        }
        
    }
    state parse_reth {
        pkt.extract(hdr.ib_reth);
        transition accept;
    }
}


/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
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
    action ipv4_forward(ipv4_addr_t switch_ip, ipv4_addr_t host_ip, bit<48> switch_mac,  bit<48> host_mac, udp_port_t switch_port) {
        hdr.ethernet.msrc_addr = switch_addr;
        hdr.ethernet.mst_addr = host_mac;
        hdr.ipv4.src_addr=switch_ip;
        hdr.ipv4.dst_addr=host_ip;
        hdr.udp.src_port=switch_port
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dst_addr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = drop;
    }

    apply {
        if (hdr.ib_bth.opcode==READ_RESPONSE_FIRST or READ_RESPONSE_MIDDLE or  READ_RESPONSE_LAST) {
            ipv4_lpm.apply();
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action translate(addr_t mount_raddr, rkey_t mount_rkey) {
        hdr.ib_reth.setValid();
        hdr.ib_reth.r_key = mount_rkey;
        hdr.ib_reth.raddr=mount_raddr;
    }

    table rdma_translate {
        key = {
            hdr.ipv4.dst_addr       : lpm;
        }
        actions = {
            translate;
            NoAction;
        }
        size = 512;
    }    
    apply{
        if(hdr.ib_reth.isValid())
        {
            rdma_translate.apply();
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

control MyDeparser(packet_out pkt, in headers hdr) {
    apply {
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.udp);
        pkt.emit(hdr.ib_bth);
        pkt.emit(hdr.ib_reth);
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
