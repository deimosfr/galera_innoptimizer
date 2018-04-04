Galera Innoptimizer
===================

NOTE: I'm not using Galera anymore that's why I won't be able to maintain this tool properly. Feel free to send pull requests anyway, I'll merge them.

Running an optimize on InnoDB tables in a Galera cluster will launch an optimize **on every nodes**. This is usually a **big problem when using huge tables**. This tool makes online InnoDB optimize on a Galera single node **without tables lock feeling on the user side**.

Galera has an OSU mode called RSU which permit to perform online schema upgrades. This mode is used by Galera Innoptimizer to perform optimize on tables. The advantage of that solution is you can still perform write (and read of course) updates while running . It won't be replicated on any nodes, simply running locally.

**Galera Innoptimizer will help you to perform all the necessary actions to optimize tables in the most easy and secure way.**

Requirements
------------

To make this tool working, you need those elements installed:

* python
* python colorama library
* python mysqldb library

If you're running Debian/Ubuntu, you can install this with this line:

```
aptitude install python-mysqldb python-colorama
```

On CentOS 6, you can install with:

    yum install -y python-setuptools MySQL-python
    easy_install pip
    pip install colorama argparse

How does it work?
-----------------

Galera has a mode which is generaly used to perform online schema upgrade, which is called RSU mode.
On a running Galera cluster, the default mode is TOI.

Galera Innoptimizer is doing:

* first check the node status to be sure it is in a normal state and exit if not
* then validate some wsrep parameter and change them if not optimal to start switching to RSU mode
* get the table list from the desired databases
* for each tables:
 * checking that the flow control paused value is enough smaller to start entering RSU mode. If it's not the case, it will wait 30 sec and re-checking until the value is correct.
 * entering RSU mode
 * optimizing table
 * if partitionning detected, rebuild each of them instead of optimizing table
 * retoring TOI mode

If during an optimize the Galera workload is too high on the current table, it will abord optimize and jump to the next table. You are notified of each status for each tables.


How to launch it?
-----------------

You can have a look at the available parameters:

```
usage: ginnoptimizer.py [-h] -d DATABASES [-u USERNAME] [-p PASSWORD]
                        [-H HOSTNAME] [-f FCPMAX] [-v]

Safetly run InnoDB Optimize on a single Galera node

optional arguments:
  -h, --help            show this help message and exit
  -d DATABASES, --databases DATABASES
                        Select the databases coma separated (specify all for
                        all databases) (default: None)
  -u USERNAME, --username USERNAME
                        Database username (default: root)
  -p PASSWORD, --password PASSWORD
                        Database password (default: )
  -H HOSTNAME, --hostname HOSTNAME
                        Database hostname (default: localhost)
  -f FCPMAX, --fcpmax FCPMAX
                        Maximum allowed flow control paused (default: 0.3)
  -v, --version         Print version number
```

You can then launch it like that to perform all databases with default username and password:

```
> ./ginnoptimizer.py -d all
[+] Trying to connect to MySQL/MariaDB instance...OK
[+] Getting all databases...OK
[+] Checking current Galera state...
  -> wsrep_ready status...OK
  -> wsrep_cluster status...OK
  -> wsrep_connected status...OK
  -> wsrep_desync status...OK
  -> wsrep_OSU_method status...OK
[+] Getting list of all tables in database1 database...OK
[+] Enabling RSU mode...OK
[+] Starting optimization on database1 database...
  -> wsrep_flow_control_paused status > 0.3...OK
  -> optimizing tablename in progress...OK
[+] Restoring TOI mode...OK
[+] Getting list of all tables in database2 database...OK
[+] Enabling RSU mode...OK
[+] Starting optimization on database2 database...
  -> wsrep_flow_control_paused status > 0.3...OK
  -> optimizing tablename1 in progress...OK
  -> wsrep_flow_control_paused status > 0.3...OK
  -> optimizing tablename2 in progress...OK
[+] Restoring TOI mode...OK
Done !
```

License
-------

GPL


ChangeLog
---------

* v0.2:
 * Adding table partitionning support (MariaDB 5.5 only for the moment, not MariaDB 10)


* v0.1:
 * First release


Contributions
-------------

Puppet modules:
- https://forge.puppet.com/jgazeley/galera_innoptimizer

Thanks to:
- Mark Wadham
- Guillaume Lefranc
- Gert Van Gool

Author Information
------------------

Pierre Mavro / deimosfr

