#!/bin/bash
#
# gd-lsh-config-sync This starts and stops gd-lsh-config-sync
#
# chkconfig: 2345 98 88
# description: gd-ssl-sync is a daemon that syncs SSL cert data from an alternate
#              data store - in this case a MySQL database.  Files are stored in
#              /var/linhosting/users structure.  Configuration is written to
#              ssl-multicert and traffic_line is called to trigger a traffic server
#              configuration reload.
#
### BEGIN INIT INFO
# Provides: gd-ssl-sync
# Required-Start: $local_fs
# Required-Stop: $local_fs
# Default-Start:  2 3 4 5
# Default-Stop: 0 1 6
### END INIT INFO

# Source function library.
. /etc/init.d/functions


RETVAL=0

prog=gd-ssl-sync
exec=/usr/local/sbin/$prog
lockfile=/var/lock/subsys/$prog
pidfile=/var/run/${prog}.pid

case "$1" in
  start)
    echo "Starting ${exec}"
    # Start the daemon
    python ${exec}.py start
    ;;
  stop)
    echo "Stopping ${exec}"
    # Stop the daemon
    python ${exec}.py stop
    ;;
  restart)
    echo "Restarting ${exec}"
    python ${exec}.py restart
    ;;
  status)
    echo "Status of ${exec}"
    python ${exec}.py status
    ;;
  *)
    echo "Usage: /etc/init.d/gd-ssl-sync {start|stop|restart|status}"
    exit 1
    ;;
esac

exit $RETVAL

