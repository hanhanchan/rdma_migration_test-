
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
            UDP_ROCE_V2 : parse_bth;
            transition accept;
        }
    }
    state parse_bth {
        pkt.extract(hdr.bth);
        transition select(hdr.bth.opcode) {
            RC_RDMA_WRITE_FIRST  : parse_reth;
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

control MyVerifyChecksum(out headers hdr, out metadata meta) {
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
    action l3_forward(bit<16> port) {
       standard_metadata.egress_spec = port;
    }

    table ip_forward {
        key = {
            hdr.ipv4.dst_addr : exact;
        }
        actions = {
            l3_forward;
            multicast;
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
 
    action fill_in_roce_fields(mac_addr_t dest_mac, ipv4_addr_t dest_ip, bit<16> mount_port, mac_addr_t mount_mac, ipv4_addr_t mount_ip) {
 

        hdr.ethernet.setValid();
        hdr.ethernet.dst_addr = dest_mac;
        hdr.ethernet.src_addr =mount_mac;
        hdr.ipv4.hdr_checksum = 0; // To be filled in by deparser or remain unchanged; todo 
        hdr.ipv4.src_addr = mount_ip;
        hdr.ipv4.dst_addr = dest_ip;

        // Set base IPv4 packet length; will be updated later based on
        // payload size and headers
        hdr.ipv4.total_len = ( \
            hdr.ib_icrc.minSizeInBytes() + \
            hdr.ib_bth.minSizeInBytes() + \
            hdr.udp.minSizeInBytes() + \
            hdr.ipv4.minSizeInBytes());

        // Update IPv4 checksum
        meta.update_ipv4_checksum = true;

        hdr.udp.src_port =mount_port; // same to fixed mount server 
        hdr.udp.checksum = 0; // disabled for RoCEv2

        // Count send; todo 
    }    
    action fill_in_reth_fields(bit<64> mount_raddr, rkey_t mount_rkey)
    {
        hdr.ib_reth.setValid();
        hdr.ib_reth.r_key = mount_rkey;
        hdr.ib_reth.addr=mount_raddr;
    }
    table create_roce_packet {
        key = {
           standard_metadata.egress_spec:exact;  // packet from host server
        }
        actions = {
            fill_in_roce_fields;
            fill_in_reth_fields;
        }
        size = 1024;
    }
    // todo: add qpn and psn
    
    // create to save 
 
 
    
    apply{
        if(hdr.ib_bth.opcode==RC_RDMA_WRITE_FIRST)
        {
            fill_in_roce_fields.apply();
            fill_in_reth_fields.apply();
        }
        else
        {
            fill_in_roce_fields.apply();
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
        pkt.emit(hdr.r);
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
