/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>
#include "configuration"
#include "types"
#include "headers"


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
            default  : parse_rpc_rdma;
        }
    }

    state parse_reth {
        pkt.extract(hdr.reth);
        transition accept;
    }
    state parse_rpc_rdma {
        pkt.extract(hdr.rpc_rdma)
        transition select(hdr.rpc_rdma.rmsg_type){
            0: parse_reply_chunk1 ;
            1: accept;
        }
    }
    state parse_reply_chunk1 {
        pkt.extract(hdr.reply_chunk1);
        transaction parse_reply_chunk2 ; //default two chunk 
    }
    state parse_reply_chunk2 {
        pkt.extract(hdr.reply_chunk2);
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
    typedef<4 bit> forward_times_t; //other server to process the request 
    register<client_info_t,  mount_point_t>(LOW_CONCURRENT)  client_info; //one operation per client 
    register<forward_times_t, mount_point_t>(LOW_CONCURRENT)  offload_flag;  
    register<server_set_t, xid_t>(LOW_CONCURRENT)  host_set;

    register <src_map_t, mount_point> reroute ; //knowns rdma operation's original XID 

    if hdr.dst=mount_point{
        apply action reroute 
    }

    table 

    action check_offload_flag()
    {
         no duplicate xid, then add to client_info
         forward_times_t+=1
    }
    action save_host()
    {
        update host_set
    }
    action reroute_client(xid)
    {
        multiple return =client_info read
        change ip,
        if first rdma, change reth
        change psn later 
    }
    action add_entry()
    table key: 1. add server 1, server 2... 
    match register host_set...
    action reroute_client()
    register server_map <server_address_t, index>
    

    if forward_times_t>2: apply table reroute_client

    table reroute_to_client
    {
        key=
    }

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
    action rewrite psn
    action rewrite basic_info
    action rewrite reth
    action for first_packet {rewrite reth; rewrite basic_info; rewrite psn} //all rdma needs rewrite psn 
    action for second_packet


    register<encode_t,ipv4_addr_t> encode_ip_reg;
    action decode_src_dst()
    { 
        \\simple map
        temp_src;
        temp_dst;
        temp_all;
        encode_ip_reg.read(temp_src,hdr.src)
        encode_ip_reg.read(temp_dst,hdr.dst)
        temp_all=temp_src+temp_dst
        hdr.offload_pair=temp_all
        
    
    }

    typdef bit<2> times_t;
    typdef bit<4> offload_pair_t;
    const times_t OFFLOAD_THRESHOLD=2;
    register<times_t,xid> recog_xid_reg;
    register<sequence_number_t,ipv4_addr_t> psn_reg;
    register<offload_pair_t,xid_t> offload_pair_reg;
    register<rhandle_t,xid_t> rhandle_reg;
    register<dma_len_t,xid_t> dma_len_reg;
    register<roffset_t,xid_t> roffset_reg;

    apply{
 
        for nfs operation:
            //register psn
            psn_reg.write(hdr.dst, hdr.psn);  //update to new value, todo: check mechanism; 
            // update forward nfs times
            times_t  temp_times; //equals to maxmize backend;
            recog_xid_reg.read(temp_times,hdr.rpc.xid);
            temp_times=temp_times+1;
            recog_xid_reg.write(hdr.rpc.xid,temp_times);
            if (temp_times > OFFLOAD_THRESHOLD)  //reroute rdma 
            {
                decode_src_dst.apply()
                offload_pair_reg.write(hdr.offload_pair,xid_t) // todo: one xid maps to multiple offload_pair
            }
            else
            {
                // add client info, per item per register 
                rhandle_reg.write(hdr.handle,xid);
                dma_len_reg.write(hdr.dma,xid);
                roffset_reg.write(hdr.roffset,xid);

            }


                // todo challenge: when multiple host servers, last nfs forward packet cross with first rdma write 
                // assume that forward_times_t knowns, for simplicity, 
        for rdma operation:
            decode_src_dst.apply()
            temp_xid;
            if (offload_pair_reg.read(temp_xid,hdr.offload_pair) has value)
            {
                \\for which destination 
                if op.code==first_packet
                    table first_reroute.apply()
                if second...
            }
 
    }
    todo: ack rules
    ack switch's psn 
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
   // todo: discriminate send/write 
   // for write first 
   // similar to bitmap?
   // reduce to one dimenson register 
   example: register<type1, type2> (num);
   register<bit<16>>(LOW_CONCURRENT,REPLY_CHUNK)  crkey;
   register<bit<8>>(LOW_CONCURRENT,REPLY_CHUNK)  bmaxlen;
   register<bit<64>>(LOW_CONCURRENT,REPLY_CHUNK)  cvaddres;
   register to_client_path(LOW_CONCURRENT)
   action reroute()
   {
       //rewrite header to  client ;
       // change ip ..
       // change header ...
       // if first
       // bind psn register 
   }
   action reset_psn()
   {
       // before update 
       // after rpc response 
   }
   action update_psn()
   //if(offload_flag== yes)
   apply(reroute())

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

        if(reply_chunk1_h.isValid()){
            crkey.write(reply_chunk1_h, reply_chunk1_h.rhandle);
            bmaxlen.write(reply_chunk1_h,reply_chunk1_h.dma_len);
            cvaddres.write(reply_chunk1_h,reply_chunk1_h.roffset);
        }
        if(reply_chunk2_h.isValid()){
            crkey.write(reply_chunk2_h, reply_chunk2_h.rhandle);
            bmaxlen.write(reply_chunk2_h,reply_chunk2_h.dma_len);
            cvaddres.write(reply_chunk2_h,reply_chunk2_h.roffset);
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
