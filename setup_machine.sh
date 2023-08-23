#server 1:
sudo ifconfig eth1 down
sudo ifconfig eth1 192.168.56.3
sudo ifconfig eth1 up 
sudo rdma link add rxe_0 type rxe netdev eth1 

#server 2:
sudo ifconfig eth1 down
sudo ifconfig eth1 192.168.56.4
sudo ifconfig eth1 up 
sudo rdma link add rxe_0 type rxe netdev eth1 

#bmv2：
sudo ifconfig eth1 down
sudo ifconfig eth1 192.168.56.10
sudo ifconfig eth1 up 
sudo rdma link add rxe_0 type rxe netdev eth1 


sudo ifconfig eth2 down
sudo ifconfig eth2 192.168.56.10
sudo ifconfig eth2 up 
sudo rdma link add rxe_1 type rxe netdev eth2 

#gw

#mount
