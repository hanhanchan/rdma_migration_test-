#include <stdio.h>
#include <stdlib.h>
#include <rpc/rpc.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <nfs/nfs.h>
#include <nfs/nfs_clnt.h>
const ip_addr="192.168.56.3"
typedef struct {
    fhandle3 handle;
} nfs_fh3;
CLIENT *cl;
cl = clnt_create(ip_addr, NFS_PROGRAM, NFS_V3, "tcp");
if (cl == NULL) {
    clnt_pcreateerror(ip_addr);
    exit(1);
}
// 假设服务器上要写入的文件为"/shared_files/example.txt"
nfs_fh3 file_handle;
memset(&file_handle, 0, sizeof(file_handle));

// 调用nfsproc3_lookup来获取文件句柄
LOOKUP3res *lookup_res;
lookup_res = nfsproc3_lookup_3(&file_handle, "/shared_files/example.txt", cl);
if (lookup_res == NULL || lookup_res->status != NFS3_OK) {
    fprintf(stderr, "Lookup file failed\n");
    exit(1);
}

// 准备写入数据
char *write_data = "Hello, NFS!"; // 将要写入的数据
size_t data_len = strlen(write_data);
WRITE3res *write_res;
write_res = nfsproc3_write_3(&file_handle, data_len, 0, write_data, cl);
if (write_res == NULL) {
    clnt_perror(cl, "Write to NFS server failed");
    exit(1);
}

if (write_res->status != NFS3_OK) {
    fprintf(stderr, "Write to NFS server failed with status: %d\n", write_res->status);
    exit(1);
}

printf("Write to NFS server successful!\n");
clnt_destroy(cl);
free(file_handle.handle.data.data_val);
