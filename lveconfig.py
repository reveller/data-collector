#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import datetime
from shutil import copyfile

from configobj import ConfigObj
#from sslutils import swapInNewFile
import ssllog






class SSLConfigTests(unittest.TestCase):

    def test_readConfig_Success(self):
        myConfig = SSLConfig()
        self.failUnless(myConfig.readConfig() and myConfig.sleepSecs == 5)

    def test_readConfig_Fail(self):
        myConfig = SSLConfig()
        self.failIf(myConfig.readConfig() and myConfig.sleepSecs != 5)

    def test_writeConfig_Success(self):
        myConfig = SSLConfig()
        myConfig.readConfig()
        self.failUnless(myConfig.writeConfig())

    def test_writeConfig_Fail(self):
        myConfig = SSLConfig()
        myConfig.readConfig()
        self.failIf(not myConfig.writeConfig())



class ConfigFile:
    def writeConfig(self):
        configFile    = self.configFilename
        bakConfigFile = configFile + ".bak"
        try:
            ssllog.log.main_logger.debug("Copying original [%s] to a backup [%s]" % \
                    (configFile, \
                     bakConfigFile))
            copyfile(configFile, bakConfigFile)
        except IOError, e:
            ssllog.log.main_logger.error("Error: Problem making a backup of [%s] to [%s]" % (configFile, bakConfigFile))
            ssllog.log.main_logger.error("Error %d: %s" % (e.args[0],e.args[1]))

        try:
            ssllog.log.main_logger.debug("Writing new config to %s" % (configFile))
            self.config.filename = configFile
            self.config.write()
        except IOError, e:
            ssllog.log.main_logger.error("Error: Problem with writing config file")
            ssllog.log.main_logger.error("Error %d: %s" % (e.args[0],e.args[1]))
            ssllog.log.main_logger.error("Error: Restoring original [%s] from backup [%s]" % \
                    (configFile, \
                     bakConfigFile))
            copyfile(bakConfigFile, configFile)
            return None
        finally:
            #            swapInNewFile(self.configFilename, newConfigFile, bakConfigFile)
            return True

class SSLConfigTimestamp(ConfigFile):

    def __init__(self, configFilename="/etc/sysconfig/gd-ssl-sync.timestamp"):
        self.configFilename            = configFilename
        self.lastMySQLTimestamp        = None
        self.lastTimestamp             = None
        self.config                    = ConfigObj(self.configFilename)
        self.readConfig()

    def readConfig(self):
        self.lastMySQLTimestamp        = self.config['LastTimestamp']
        self.lastTimestamp             = datetime.datetime.strptime(self.lastMySQLTimestamp, '%Y-%m-%d %H:%M:%S')
        return True

class SSLConfig(ConfigFile):

    def __init__(self, configFilename="/etc/sysconfig/gd-ssl-sync.conf"):
        self.configFilename            = configFilename
        self.logFilename               = None
        self.logLevel                  = None
        self.sleepSecs                 = None
        self.sslCertDestinationPath    = None
        self.atsSSLMultiCertConfigFile = None
        self.atsRemapConfigFile        = None
        self.atsTrafficLinePath        = None
        self.databaseHost              = None
        self.databaseUser              = None
        self.databasePass              = None
        self.databaseName              = None
        self.config                    = ConfigObj(self.configFilename)
        self.readConfig()

    def readConfig(self):
        self.sleepSecs                 = int(self.config['SleepSecs'])
        self.logFilename               = self.config['LogFile']
        self.logLevel                  = self.config['LogLevel']
        self.sslCertDestinationPath    = self.config['SSLDestinationPath']
        self.atsSSLMultiCertConfigFile = self.config['ATSSSLMultiCertConfigFile']
        self.atsRemapConfigFile        = self.config['ATSRemapConfigFile']
        self.atsTrafficLinePath        = self.config['ATSTrafficLinePath']
        self.databaseHost              = self.config['DatabaseHost']
        self.databaseUser              = self.config['DatabaseUser']
        self.databasePass              = self.config['DatabasePass']
        self.databaseName              = self.config['DatabaseName']
        return True


sslConfig          = SSLConfig("/etc/sysconfig/gd-ssl-sync.conf")
sslConfigTimestamp = SSLConfigTimestamp("/etc/sysconfig/gd-ssl-sync.timestamp")


def main():
    unittest.main()

if __name__ == '__main__':
    main()

