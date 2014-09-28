#!/bin/bash

if [ -z $1 ] ; then
    echo "Enter a database name"
    exit 1
fi

hostname=$(cat /etc/hostname)
db=$1

mysql << EOF
insert into $db.sbtest values('',15,'$hostname','mytestmytestmytestmytestmytest');
insert into $db.sbtest values('',15,'$hostname','mytestmytestmytestmytestmytest');
select * from $db.sbtest where pad = mytestmytestmytestmytestmytest');
EOF
