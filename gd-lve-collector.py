#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import datetime
import time
import sys
import socket
import signal
import optparse
import MySQLdb as mdb
from daemon import runner

import sslconfig
import ssllog

class App:

    def __init__(self):
        self.stdin_path      = '/dev/null'
        self.stdout_path     = '/dev/null'
        self.stderr_path     = '/dev/null'
        self.pidfile_path    = '/var/run/gd-lve-collector.pid'
        self.pidfile_timeout = 5

    def run(self):
        main()

def main():

    cont = 1

    ssllog.log.initLog(sslconfig.sslConfig.logFilename, sslconfig.sslConfig.logLevel)
    if options.runOnceMode:
        ssllog.log.enableLogToConsole()

    ssllog.log.main_logger.debug("Starting main()")

    sleepInSecs            = sslconfig.sslConfig.sleepSecs
    sslCertDestinationPath = sslconfig.sslConfig.sslCertDestinationPath
    lastTimestamp          = sslconfig.sslConfigTimestamp.lastTimestamp

    myHostname = socket.gethostname()
    ssllog.log.main_logger.info("My hostname: " + myHostname)

    datastore = SSLDataStore(sslconfig.sslConfig.databaseHost, \
        sslconfig.sslConfig.databaseUser, \
        sslconfig.sslConfig.databasePass, \
        sslconfig.sslConfig.databaseName)

    if not datastore:
        ssllog.log.main_logger.critical("Error: Problem connecting to the "\
                "database. Exiting!")
        exit(2)

    #
    # Let's see whats changed since we were last here
    #
    dbConnected = 0
    dbSleep = 60
    while not dbConnected:
        try:
            datastore.connect()
        except mdb.Error, e:
            ssllog.log.main_logger.error("Error: Problem getting current state " \
                    "from the database. Sleeping for %d before trying again." \
                    % (dbSleep))
            ssllog.log.main_logger.error("Error %d: %s" % (e.args[0],e.args[1]))
            time.sleep(dbSleep)

        if datastore.con and datastore.con.open:
            dbConnected = 1
            datastore.cursor = datastore.con.cursor()

            # Parse out the starting ss-multicert.conf file into a hash (past
            # state)
            pastSSLConfigHash = atsParseSSLMultiCertConfig()
            # Grab all of the XIDs in the SSL datastore (present state)
            originTimestamp = datetime.datetime(1970, 1, 1, 0, 0, 0)
            presentSSLConfigHash = sslcertdatabase.getXIDsNewerThanTimestamp(\
                    datastore, originTimestamp)
        else:
            ssllog.log.main_logger.error("Error: Problem getting opening " \
                    "connection to database in order to obtain the current " \
                "state from the database. Sleeping for %d before trying again." \
                    % (dbSleep))
            time.sleep(dbSleep)

    # Now lets figure out the differences
    if presentSSLConfigHash or pastSSLConfigHash:
        dictDiffs = DictDiffer(presentSSLConfigHash, pastSSLConfigHash)

        removedList = list(dictDiffs.removed())
        if removedList:
            removedStr  = ', '.join(str(each) for each in removedList)
            ssllog.log.main_logger.debug("Removed: %s", removedStr)
            sslcertdatabase.deleteListOfCerts(removedList, sslCertDestinationPath)

        addedList = list(dictDiffs.added())
        if addedList:
            addedStr  = ', '.join(str(each) for each in addedList)
            ssllog.log.main_logger.debug("Added: %s", addedStr)
            sslcertdatabase.writeCertsFromListOfXIDs(datastore, addedList, sslCertDestinationPath)

        limitStart = 0
        while 1:
            # grab certs WHERE (ssl_date_inserted >= the last time we checked
            # (which we get from the latest record we got from the database
            #
            # There will be some duplicated effort here.  This is to prevent
            # the scenario that certs were written to the database a split
            # second (literally within the same second) as the last time we
            # pulled records.
            # In order to avoid missing any records, I chose to pull records that
            # had been inserted/updated >= to the last time we checked versus
            # just checking > the last time we checked.  The duplicated effort
            # will be minimal, and since we are going to have to trigger a
            # reload of the ats config anyway, it shouldn't matter.  We will
            # just write one to a few certs again from the last run (that match
            # the timestamp to the second).
            changedCertHash, thisTimestamp = sslcertdatabase.getCertsNewerThanTimestamp(\
                    datastore, lastTimestamp, limitStart, 1000)
            if thisTimestamp:
                lastTimestamp = thisTimestamp
            if not changedCertHash:
                break
            limitStart += 1000
            ssllog.log.main_logger.debug("- Write certs to filesystem %s" %\
                    ', '.join(['%s' % (key) for key in changedCertHash.keys()]))
            sslcertdatabase.writeCertsFromHashOfCerts(changedCertHash, sslCertDestinationPath)

    # We should be up to date with our files now, lets update the ats
    # ssl-multicert.conf file and tell traffic_line to reload the config
    atsUpdateSSLMultiCertConfigFromConfigHash(presentSSLConfigHash, 'w')
    atsUpdateRemapConfigFromConfigHash(presentSSLConfigHash, 'w')
    atsReloadConfig()
    datastore.close()

    # Now that we are caught up, update the last check timstamp in the config
    # file before we drop into the main loop
    sslconfig.sslConfigTimestamp.config['LastTimestamp'] = lastTimestamp.strftime('%Y-%m-%d %H:%M:%S')

    while cont:
        try:
            datastore.connect()
            if datastore.con.open:
                datastore.cursor = datastore.con.cursor()
                changed = sslserverdatabase.getServerChangedFlag(datastore, myHostname)
            else:
                ssllog.log.main_logger.error("Error: Problem with the database.")
        except mdb.Error, e:
            ssllog.log.main_logger.error("Error %d: %s" % (e.args[0],e.args[1]))

        if changed:
            ssllog.log.main_logger.debug("My changed flag is set to '1' - I should do something!")

            # Mark this as the beginning of the update cycle (cuz we know we
            # have someting to do now), so lets update the timestamp, but dont
            # write our config file until we are done in case something
            # happens - a built in do-over
            ssllog.log.main_logger.debug("- Update the lastTimestamp in our internal config "\
                    ", converted to MySQL")
            sslconfig.sslConfigTimestamp.config['LastTimestamp'] = lastTimestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Lets take care of any recent adds or updates to the database
            # first.  Here, we loop through the queries in 'pages' to avoid
            # using too much memory.  (Image trying to load 100,000s of records
            # into memory at once!)
            ssllog.log.main_logger.debug("- Get certs inserted since %s" \
                    % lastTimestamp.strftime('%Y-%m-%d %H:%M:%S'))
            limitStart = 0
            while 1:
                # grab certs WHERE (ssl_date_inserted >= the last time we checked
                # (which we get from the latest record we got from the database
                sslCertHash, thisTimestamp = sslcertdatabase.getCertsNewerThanTimestamp(\
                        datastore, lastTimestamp, limitStart, 1000)
                if thisTimestamp:
                    lastTimestamp = thisTimestamp
                if not sslCertHash:
                    break
                limitStart += 1000
                # Write out the new/updated certs we found in the database
                ssllog.log.main_logger.debug("- Write certs to filesystem %s" %\
                        ', '.join(['%s' % (key) for key in sslCertHash.keys()]))
                sslcertdatabase.writeCertsFromHashOfCerts(sslCertHash, sslCertDestinationPath)

            # Now snapshot the entire database and see if there are any
            # 'delete's
            # Grab all of the XIDs in the SSL datastore (new state)
            ssllog.log.main_logger.debug("- Getting a fresh look at the database to see if anything was deleted")
            originTimestamp = datetime.datetime(1970, 1, 1, 0, 0, 0)
            newSSLConfigHash = sslcertdatabase.getXIDsNewerThanTimestamp(datastore, originTimestamp)

            # We've added the new/updated cert files, but before we delete
            # any files, lets write out the new ssl-multicert config based on
            # the most recent snapshot of the database which includes adds,
            # updates and deletes.
            #
            # Tell traffic_line to trigger a reload of the trafficserver
            # config.  We can take care of deleting the old files while it is
            # coming back up.
            ssllog.log.main_logger.debug("- Update trafficserver ssl-multicert")
            atsUpdateSSLMultiCertConfigFromConfigHash(newSSLConfigHash, 'w')
            atsUpdateRemapConfigFromConfigHash(newSSLConfigHash, 'w')
            ssllog.log.main_logger.debug("- Trigger traffic_line to reload config")
            atsReloadConfig()

            # Now lets figure out the differences to see if there are any
            # deletes
            ssllog.log.main_logger.debug("- Figuring out the differences since our last update to see what was deleted")
            if newSSLConfigHash or presentSSLConfigHash:
                dictDiffs = DictDiffer(newSSLConfigHash, presentSSLConfigHash)

                removedList = list(dictDiffs.removed())
                if removedList:
                    removedStr  = ', '.join(str(each) for each in removedList)
                    ssllog.log.main_logger.debug("- Records have been removed from the database: %s" % (removedStr))
                    ssllog.log.main_logger.debug("- Removing cert files for records deleted from database")
                    sslcertdatabase.deleteSetOfCerts(removedList, sslCertDestinationPath)

            # We should be up to date with our cert files now, lets update our
            # hash to the most recent one
            ssllog.log.main_logger.debug("- Updating my internal hash of cert info")
            presentSSLConfigHash = newSSLConfigHash

            # Update our own changed_flag in the database, cux we're done!
            ssllog.log.main_logger.debug("Resetting my changed flag, cuz I am done")
            if not sslserverdatabase.updateServerChangedFlag(datastore, myHostname, 0):
                ssllog.log.main_logger.error("Error: Unable to update the Server Changed Flag")
                ssllog.log.main_logger.error("Error %d: %s" % (e.args[0],e.args[1]))

            # all done, lets update our config file with the timstamp of this
            # completed update
            ssllog.log.main_logger.debug("- Update the timestamp in the config for the next go round to %s" \
                    % lastTimestamp.strftime('%Y-%m-%d %H:%M:%S'))
            sslconfig.sslConfigTimestamp.config['LastTimestamp'] = lastTimestamp.strftime('%Y-%m-%d %H:%M:%S')
            sslconfig.sslConfigTimestamp.writeConfig()

        datastore.close()

        time.sleep(sleepInSecs)


#
# I hate running this here, but it is the only way to make the parsed options global in scope.
#
parser = optparse.OptionParser()
parser.add_option('-d', '--daemon', help='Run in daemon mode', dest='daemonMode', default=False, action='store_true')
parser.add_option('-n', '--run-once', help='Run once mode (non-daemon)', dest='runOnceMode', default=False, action='store_true')
(options, args) = parser.parse_args()

if __name__ == '__main__':

    # TODO make this work at some point in the future.  For now, it works if
    # you use --run-once to run it once since it gets acted on first.
    #
    # daemon_runner grabs the args and insists that [start|stop|restart]
    # are the only options.
    if options.runOnceMode == True:
        main()
#    elif options.daemonMode == True:
    else:
        if len(sys.argv) > 1:
            if 'start' in sys.argv:
                print "Starting %s in daemon mode" % sys.argv[0]
            elif 'stop' in sys.argv:
                print "Stopping %s daemon mode" % sys.argv[0]
            elif 'status' in sys.argv:
                try:
                    # TODO make this a directive in the config file 
                    pf = file('/var/run/gd-ssl-sync.pid','r')
                    pid = int(pf.read().strip())
                    pf.close()
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise # re-raise exception if a different error occured
                except IOError:
                    pid = None
                except SystemExit:
                    pid = None

                if pid:
                    print "%s is running as pid %s" % (sys.argv[0], pid)
                    sys.exit(0)
                else:
                    print "%s is not running." % sys.argv[0]
                    sys.exit(1)
        app = App()
        daemon_runner = runner.DaemonRunner(app)
        daemon_runner.do_action()
#    else:
#        parser.print_help()


