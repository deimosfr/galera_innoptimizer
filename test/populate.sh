#!/bin/bash

echo "Deleting old databases"
mysql << EOF
drop database database1;
drop database database2;
drop database database3;
drop database database4;
EOF

echo "Create 4 databases"
mysql << EOF
create database database1;
create database database2;
create database database3;
create database database4;
EOF

echo "Populate the 4 databases"
sysbench --test=oltp --db-driver=mysql --mysql-table-engine=innodb --mysql-user=root --mysql-password='' --mysql-host=localhost --mysql-port=3306 --oltp-table-size=7500000  --mysql-db=database1 prepare
sysbench --test=oltp --db-driver=mysql --mysql-table-engine=innodb --mysql-user=root --mysql-password='' --mysql-host=localhost --mysql-port=3306 --oltp-table-size=7500000  --mysql-db=database2 prepare
sysbench --test=oltp --db-driver=mysql --mysql-table-engine=innodb --mysql-user=root --mysql-password='' --mysql-host=localhost --mysql-port=3306 --oltp-table-size=7500000  --mysql-db=database3 prepare
sysbench --test=oltp --db-driver=mysql --mysql-table-engine=innodb --mysql-user=root --mysql-password='' --mysql-host=localhost --mysql-port=3306 --oltp-table-size=7500000  --mysql-db=database4 prepare

echo "Delete some data in the 4 databases"
mysql << EOF
delete from database1.sbtest where id < 12000000;
delete from database2.sbtest where id > 12000000;
delete from database3.sbtest where id < 13000000;
delete from database4.sbtest where id > 13000000;
EOF

