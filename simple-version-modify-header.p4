/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>
#include "types.p4"
#include "headers.p4"


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
            RC_RDMA_WRITE_FIRST: parse_reth;
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
    

    action multicast() {
        standard_metadata.mcast_grp = 1;
    }
    action l3_forward(bit<9> port) {
       standard_metadata.egress_spec = port;
    }

    table ip_forward {
        key = {
            hdr.ipv4.dst_addr : lpm;
        }
        actions = {
            l3_forward;
            //multicast;
            NoAction;
        }
        size = 512;
    }

    apply {
        ip_forward.apply();
    } 
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // Get client MAC and IP and form RoCE output packets
    // (Sequence number and queue pair will be filled in later)
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action fill_in_roce_fields(mac_addr_t dest_mac, ipv4_addr_t dest_ip, bit<16> mount_port, mac_addr_t mount_mac, ipv4_addr_t mount_ip) {
 

        hdr.ethernet.setValid();
        hdr.ethernet.mst_addr = dest_mac;
        hdr.ethernet.msrc_addr =mount_mac;
        hdr.ipv4.hdr_checksum = 0; // To be filled in by deparser or remain unchanged; todo 
        hdr.ipv4.src_addr = mount_ip;
        hdr.ipv4.dst_addr = dest_ip;

        // Set base IPv4 packet length; will be updated later based on
        // payload size and headers

        // Update IPv4 checksum
 

        hdr.udp.src_port =mount_port; // same to fixed mount server 
        hdr.udp.checksum = 0; // disabled for RoCEv2

        // Count send; todo 
    }    
    action fill_in_reth_fields(bit<64> mount_raddr, rkey_t mount_rkey)
    {
        hdr.ib_reth.setValid();
        hdr.ib_reth.r_key = mount_rkey;
        hdr.ib_reth.raddr=mount_raddr;
    }
    table create_roce_packet {
        key = {
           hdr.ipv4.dst_addr : lpm;  // packet from host server
        }
        actions = {
            drop;
            fill_in_roce_fields;
        }
        size = 1024;
    }
    // todo: add qpn and psn
    
    // create to save 
 
    table create_reth_packet {
        key = {
           hdr.ipv4.dst_addr : lpm;  // packet from host server
        }
        actions = {
            drop;
            fill_in_reth_fields;
        }
        size = 1024;
    }
    
    apply{
        create_roce_packet.apply();
        create_reth_packet.apply();

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
