#!/bin/bash

mysql << EOF
SET wsrep_on=ON;
SET GLOBAL wsrep_desync=OFF;
SET GLOBAL wsrep_OSU_method='TOI';
EOF

