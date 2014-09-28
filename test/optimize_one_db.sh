#!/bin/bash

if [ -z $1 ] ; then
    echo "Enter a database name"
    exit 1
fi

db=$1

mysql << EOF
SET GLOBAL wsrep_OSU_method='RSU';
SET GLOBAL wsrep_desync=ON; SET wsrep_on=OFF;
optimize table $db.sbtest;
SET wsrep_on=ON; SET GLOBAL wsrep_desync=OFF;
SET GLOBAL wsrep_OSU_method='TOI';
EOF
