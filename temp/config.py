import pyverbs.enums as e

ADDR_CLIENT  = "192.168.56.3"
ADDR_SERVER = "192.168.56.4" #server bound to where
''' proxy-server1
ADDR_SERVER  = "192.168.56.3"
ADDR_CLIENT= "192.168.56.4"
'''
'''switch-proxy
ADDR_SERVER  = "192.168.56.10"
ADDR_CLIENT_1  = "192.168.56.3"
ADDR_CLIENT_2 = "192.168.56.4"
'''
PORT_INT = 50008
PORT_STR = "50008"
NAME = "rocep0s8"
TIMEOUT_IN_MS = 500
# BUFFER_SIZE = 1024
# FILE_SIZE = 5 * BUFFER_SIZE * BUFFER_SIZE  # 10MB
BUFFER_SIZE = 1024
UNITS=1024
IOSIZE=32
#FILE_SIZE = 5 * BUFFER_SIZE * BUFFER_SIZE  # 10MB
FILE_SIZE=UNITS*IOSIZE
#FILE_SIZE=1024
BUFFER_META_SIZE=1024
FILE_NAME="test/test.txt"
OPTIONS = {
    "qp_init": {
        "qp_type": e.IBV_QPT_UC,
        "max_send_wr": 4,
        "max_recv_wr": 4,
        "max_send_sge": 2,
        "max_recv_sge": 2,
    },
    "cq_init": {
        "cqe": 8
    },
    "gid_init": {
        "port_num": 1,
        "gid_index": 1,  # 3 mean to use the RoCE v2 interface
    }
}
is_control_plane=False
is_pause_time=True