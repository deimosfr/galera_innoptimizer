#!/usr/bin/env python
# encoding: utf-8
# Made by Pierre Mavro / Deimosfr

# Dependancies:
# - python colorama
# - python mysqldb
# On Debian: aptitude install python-mysqldb python-colorama

# Todo:
# - add progression percentage
# - limit the number of sql connections
# - filters args on tables

import argparse
import MySQLdb
import sys
import time
from colorama import init, Fore
from datetime import datetime

hostname, username, password = ['', '', '']


def sizeof_fmt(num, suffix='B'):
    """@todo: Docstring for sizeof_fmt

    :num: size in bytes
    :type num: int
    :suffix: str
    :type suffix: str

    :returns:
    :rtype: return a human-readable string

    """
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def print_color(mtype, message=''):
    """@todo: Docstring for print_text.

    :mtype: set if message is 'ok', 'updated', '+', 'fail' or 'sub'
    :type mtype: str
    :message: the message to be shown to the user
    :type message: str

    """

    init(autoreset=True)
    if (mtype == 'ok'):
        print(Fore.GREEN + 'OK' + Fore.RESET + message)
    elif (mtype == '+'):
        print('[+] ' + message + '...'),
    elif (mtype == 'fail'):
        print(Fore.RED + "\n[!]" + message)
    elif (mtype == 'sub'):
        print(('  -> ' + message).ljust(65, '.')),
    elif (mtype == 'subsub'):
        print("\n    -> " + message + '...'),
    elif (mtype == 'up'):
        print(Fore.CYAN + 'UPDATED')


def sql_query(queries, return_list=False, exit_fail=True):
    """
    This function will pass queries to the MySQL/MariaDB instance

    :queries: list of queries to execute
    :type queries: list / tuple
    :return_list: if you need a return from the query, set it to True
    :type return_list: boolean
    :exit_fail: you can choose if the program needs to continue on fail or not
    :type exit_fail: boolean

    :returns:
    :rtype: return a list of result

    """
    db = MySQLdb.connect(host=hostname, user=username, passwd=password)
    cur = db.cursor()

    try:
        query = ' '.join(queries)
        cur.execute(query)
    except MySQLdb.Error, e:
        try:
            print_color('fail', "MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            if (exit_fail):
                restore_toi()
                sys.exit(1)
        except IndexError:
            print_color('fail', "MySQL Error: %s" % str(e))
            if (exit_fail):
                restore_toi()
                sys.exit(1)

    if return_list:
        list_to_return = list()
        for row in cur.fetchall():
            list_to_return.append(row)

    # Close all cursors and databases
    cur.close()
    db.close()

    if return_list:
        return list_to_return


def get_sorted_tables_by_size(dbname):
    """
    Getting all tables from a database, sorting them ascending by size

    :param dbname: database name
    :type dbname: str

    :returns:
    :rtype: tuple

    """

    print_color('+', "Getting list of all tables in " + dbname + " database")
    tables_list = sql_query([
        'SELECT TABLE_NAME, (data_length + index_length) AS size FROM information_schema.TABLES \
        WHERE table_schema = "' + dbname + '" AND TABLE_TYPE<>"VIEW"\
        ORDER BY (data_length + index_length);'],
        True)

    # Check select result
    if (len(tables_list) == 0):
        print_color('fail', dbname + " doesn't exist or contain tables")
        sys.exit(1)
    else:
        print_color('ok')

    return tables_list


def enable_rsu():
    """
    Enable RSU Galera mode
    """
    print_color('+', 'Enabling RSU mode')
    print ''
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_OSU_method";',
                        'wsrep_OSU_method', 'RSU',
                        'SET GLOBAL wsrep_OSU_method="RSU";')
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_desync";',
                        'wsrep_desync', 'ON', 'SET GLOBAL wsrep_desync=1;')
    print_color('ok')


def restore_toi():
    """
    Restore TOI Galera mode
    """
    print_color('+', 'Restoring TOI mode')
    print ''
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_on";',
                        'wsrep_on', 'ON', 'SET GLOBAL wsrep_on=ON;')
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_desync";',
                        'wsrep_desync', 'OFF', 'SET GLOBAL wsrep_desync=0;')
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_OSU_method";',
                        'wsrep_OSU_method', 'TOI',
                        'SET GLOBAL wsrep_OSU_method="TOI";')
    print_color('ok')


def optimize_rsu(dbname, tables_list, fcpmax):
    """
    Setting session in RSU mode, setting node in maintenance but still
    receiving updated data. Then optimize table by table on the selected
    database. When finished, restoring TOI mode.

    :dbname: database name
    :type dbname: str
    :tables_list: list of table to proceed
    :type tables_list: list

    :returns:
    :rtype: dict

    """

    def print_formatted_results(optimize_start, table_size):
        """
        Print OK along with some optimization performance data

        :optimize_start: time of optimization start
        :type optimize_start: datetime
        :table_size: size of table/partition
        :type table_size: int

        """

        time_spent = (datetime.now() - optimize_start).total_seconds()
        print_color('ok', ' (' + '{:.1f}'.format(time_spent) + 's; ' + sizeof_fmt(table_size/time_spent) + '/s)')

    def launch_sql_queries(table, size):
        """
        Launch SQL optimize on a table
        If fail during optimize, will simply go to the next one after warning

        :table: table name
        :type table: str
        :size: size of the table
        :type size: int

        """

        # Checking if there are partitions on the current table
        ptables = sql_query(['EXPLAIN PARTITIONS select * from ' + dbname +
                             '.' + table + ';'], True)
        if ptables[0][3] == None:
          partitions = ['no partitions']
        else:
          partitions = ptables[0][3].split(',')

        # Launching query
        print_color('sub', 'optimizing ' + table + ' (' + sizeof_fmt(size) + ') in progress')
        if len(partitions) == 1:
            start_time = datetime.now()
            sql_query(['SET wsrep_on=OFF;',
                       'optimize table ' + dbname + '.' + table + ';'],
                      False, False)
            print_formatted_results(start_time, size)
        else:
            for partition in partitions:
                start_time = datetime.now()
                print_color('subsub', 'partition ' + partition +
                            ' in progress')
                print('ALTER ONLINE TABLE ' + dbname + '.' + table +
                      ' REBUILD PARTITION ' + partition + ';')
                sql_query(['SET wsrep_on=OFF;',
                           'ALTER ONLINE TABLE ' + dbname + '.' + table +
                           ' REBUILD PARTITION ' + partition + ';'],
                          False, False)
                print_formatted_results(start_time, size)
                get_wsrep_fcp(fcpmax)

    # Optimize each tables
    enable_rsu()
    print_color('+', 'Starting optimization on ' + dbname + ' database')
    print ''
    for row in tables_list:
        get_wsrep_fcp(fcpmax)
        launch_sql_queries(row[0], row[1])
    restore_toi()


def get_all_databases():
    """
    Getting all databases names

    :returns:
    :rtype: list

    """

    print_color('+', 'Getting all databases')
    tuple_databases = sql_query(['show databases;'], True)
    print_color('ok')

    # Remove internal databases that doesn't support optimize
    databases = list()
    for database in tuple_databases:
        databases.append(database[0])
    databases.remove('information_schema')
    databases.remove('mysql')
    databases.remove('performance_schema')

    return databases


def check_mysql_connection():
    """
    Check simple MySQL/MariaDB connection
    """

    try:
        print_color('+', 'Trying to connect to MySQL/MariaDB instance')
        db = MySQLdb.connect(host=hostname, user=username, passwd=password)
    except MySQLdb.Error, e:
        try:
            print_color('fail', "ERROR [%d]: %s" % (e.args[0], e.args[1]))
            sys.exit(1)
        except IndexError:
            print_color('fail', "ERROR: %s" % str(e))
            sys.exit(1)
    db.close()
    print_color('ok')


def check_and_set_param(query, param_name, value, set_param):
    """
    Checking global parameters and update them if not what we've expected

    :query: SQL query to check a status parameter
    :type query: str
    :param_name: name of the Galera parameter
    :type param_name: str
    :value: the correct value that param_name should have
    :type value: str
    :set_param: query to launch to set new parameter
    :type fail_msg: str

    """
    print_color('sub', param_name + ' status')
    wsrep_param = sql_query([query], True)
    if (wsrep_param[0][1] != value):
        sql_query([set_param])
        print_color('up')
    else:
        print_color('ok')


def check_galera_current_state():
    """
    Check Galera status to be sure the node is ready to proceed to operations
    TOI mode is enabled to be sure there won't be issues while switching to RSU
    mode.

    """

    def check_param(query, param_name, value, fail_msg):
        """
        Check Galera parameters and exit on failing

        :query: SQL query to check a status parameter
        :type query: str
        :param_name: name of the Galera parameter
        :type param_name: str
        :value: the correct value that param_name should have
        :type value: str
        :fail_msg: message to show in failure case
        :type fail_msg: str

        :returns:
        :rtype: float

        """
        print_color('sub', param_name + ' status')
        wsrep_param = sql_query([query], True)
        if (wsrep_param[0][1] != value):
            print_color('fail', fail_msg + ' (' + param_name + ' => '
                        + str(wsrep_param[0][1]) + ')')
            sys.exit(1)
        print_color('ok')
        return wsrep_param

    print_color('+', "Checking current Galera state")
    print ''
    # Mandatory checks
    check_param('SHOW STATUS LIKE "wsrep_ready";', 'wsrep_ready', 'ON',
                'Galera node seams unsynced')
    check_param('SHOW STATUS LIKE "wsrep_cluster_status";', 'wsrep_cluster',
                'Primary', 'Galera node is not in primary mode')
    check_param('SHOW STATUS LIKE "wsrep_connected";', 'wsrep_connected',
                'ON', 'Galera node is not connected')

    # Optional but required checks
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_desync";',
                        'wsrep_desync', 'OFF', 'SET GLOBAL wsrep_desync=0;')
    check_and_set_param('SHOW GLOBAL VARIABLES LIKE "wsrep_OSU_method";',
                        'wsrep_OSU_method', 'TOI',
                        'SET GLOBAL wsrep_OSU_method="TOI";')


def get_wsrep_fcp(fcpmax):
    """
    Get Flow control paused status

    :fcpmax: Flow control paused value
    :type fcpmax: float

    """

    def check_wsrep_fcp(fcpmax):
        """

        :fcpmax: @todo
        :returns: @todo

        """
        wsrep_fcp = sql_query(['SHOW STATUS LIKE "wsrep_flow_control_paused";'],
                              True)
        wsrep_fcp_value = float(wsrep_fcp[0][1])
        return wsrep_fcp_value

    print_color('sub', 'wsrep_flow_control_paused status > ' + str(fcpmax))
    wsrep_fcp_value = check_wsrep_fcp(fcpmax)
    sleeptime = 30
    while (wsrep_fcp_value > fcpmax):
        print_color('sub', 'Flow control paused is too high (' +
                    wsrep_fcp_value + ') waiting ' +
                    str(sleeptime) + 's')
        time.sleep(sleeptime)
        wsrep_fcp_value = check_wsrep_fcp(fcpmax)
    print_color('ok')


def args():
    """
    Manage args
    """

    global hostname, username, password

    databases = []

    # Main informations
    parser = argparse.ArgumentParser(
        description="Safetly run InnoDB Optimize on a single Galera node",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # Default args
    parser.add_argument('-d',
                        '--databases',
                        action='store',
                        type=str,
                        required=True,
                        metavar='DATABASES',
                        help='Select the databases coma separated \
                        (specify all for all databases)')
    parser.add_argument('-u',
                        '--username',
                        action='store',
                        type=str,
                        default='root',
                        metavar='USERNAME',
                        help='Database username')
    parser.add_argument('-p',
                        '--password',
                        action='store',
                        type=str,
                        default='',
                        metavar='PASSWORD',
                        help='Database password')
    parser.add_argument('-H',
                        '--hostname',
                        action='store',
                        type=str,
                        default='localhost',
                        metavar='HOSTNAME',
                        help='Database hostname')
    parser.add_argument('-f',
                        '--fcpmax',
                        action='store',
                        type=float,
                        default='0.3',
                        metavar='FCPMAX',
                        help='Maximum allowed flow control paused')
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='v0.1 Licence GPLv2',
                        help='Print version number')

    result = parser.parse_args()

    # Print help if no args supplied
    if (len(sys.argv) == 1):
        parser.print_help()
        sys.exit(1)

    if (result.hostname):
        hostname = result.hostname
    if (result.username):
        username = result.username
    if (result.password):
        password = result.password
    if (result.fcpmax):
        fcpmax = result.fcpmax

    # Check if connection is ok
    check_mysql_connection()

    # Check if multiple database have been requested
    # if not get all databases
    if (not result.databases):
        databases = get_all_databases()
    else:
        # Create a list from entered databases
        databases = result.databases.split(',')
        # Check if all databases are requested
        if (len(databases) == 1):
            if (databases[0] == 'all'):
                databases = get_all_databases()

    # Check Galera status before going ahead
    check_galera_current_state()

    # Optimize all requested databases
    for database in databases:
        tables_list = get_sorted_tables_by_size(database)
        optimize_rsu(database, tables_list, fcpmax)

    print 'Done !'


def main():
    """
    Main function
    """
    args()

if __name__ == "__main__":
    main()
