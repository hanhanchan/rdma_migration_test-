#转发
# write 
# 4k, 8k, 32k, 64k, 256k, 1024k
sudo fio --filename=/mnt/clienttwo/test.txt --bs=4k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=8k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=32k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=64k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=256k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=1024k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G
 
# read 
# 4k, 8k, 32k, 64k, 256k, 1024k
sudo fio --filename=/mnt/clienttwo/test.txt --bs=4k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=8k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=32k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=64k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=256k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=1024k --numjobs=4 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G


#直连 
# write 
# 4k, 8k, 32k, 64k, 256k, 1024k
sudo fio --filename=/mnt/client/test.txt --bs=4k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=8k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=32k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=64k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=256k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=1024k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-randwrite-iops --size=1G
 
# read 
# 4k, 8k, 32k, 64k, 256k, 1024k
sudo fio --filename=/mnt/client/test.txt --bs=4k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=8k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=32k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=64k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=256k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G

sudo fio --filename=/mnt/client/test.txt --bs=1024k --numjobs=4 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G



## read template 
 
#!/bin/bash
sudo fio --filename=/mnt/client/test.txt --bs=64k --numjobs=2 --ioengine=libaio --iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers --norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G &

sudo fio --filename=/mnt/clienttwo/test.txt --bs=64k --numjobs=2 --ioengine=libaio --iodepth=32 --direct=1 --rw=read --time_based --runtime=60 --refill_buffers --norandommap --randrepeat=0 --group_reporting --name=fio-read-iops --size=1G &

wait
 
## write template 

 #!/bin/bash

sudo fio --filename=/mnt/client/test.txt --bs=64k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-write-iops --size=1G

sudo fio --filename=/mnt/clienttwo/test.txt --bs=64k --numjobs=2 --ioengine=libaio \
--iodepth=32 --direct=1 --rw=write --time_based --runtime=60 --refill_buffers \
--norandommap --randrepeat=0 --group_reporting --name=fio-write-iops --size=1G

wait
