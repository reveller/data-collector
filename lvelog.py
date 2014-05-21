#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import logging
import sys
import os



class SSLLoggerTests(unittest.TestCase):

    def setUp(self):
        ssllog.log.initLog("./unittest.log", 'DEBUG')

    def test_getLogLevel_Success(self):
        self.failUnless(ssllog.log.getLogLevel('DEBUG') == logging.DEBUG)

    def test_getLogLevel_Fail(self):
        self.failIf(ssllog.log.getLogLevel('WRONG') != logging.WARNING)

class SSLLogger():

    def initLog(self, logFilename, logLevelStr):
        # make a logger
        self.main_logger = logging.getLogger(os.path.splitext(os.path.basename(sys.argv[0]))[0])

        # make some handlers
#        self.console_handler = logging.StreamHandler() # by default, sys.stderr
        self.file_handler    = logging.FileHandler(logFilename)

        # set logging levels
        self.logLevelStr = logLevelStr
        self.logLevel = self.getLogLevel(self.logLevelStr)
#        self.console_handler.setLevel(self.logLevel)
        self.file_handler.setLevel(self.logLevel)
        self.main_logger.setLevel(self.logLevel)

        # set the Formatter
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#        self.console_handler.setFormatter(self.formatter)
        self.file_handler.setFormatter(self.formatter)

        # add handlers to logger
#        self.main_logger.addHandler(self.console_handler)
        self.main_logger.addHandler(self.file_handler)


    def enableLogToConsole(self):
        self.console_handler = logging.StreamHandler() # by default, sys.stderr
        self.console_handler.setLevel(self.logLevel)
        self.console_handler.setFormatter(self.formatter)
        self.main_logger.addHandler(self.console_handler)

    def getLogLevel(self, LogLevelStr):
        return {
            'DEBUG'    : logging.DEBUG,
            'INFO'     : logging.INFO,
            'WARNING'  : logging.WARNING,
            'ERROR'    : logging.ERROR,
            'CRITICAL' : logging.CRITICAL
            }.get(LogLevelStr, logging.WARNING)

    def Debug(self, outStr):
        self.main_logger.debug(outStr)

    def Info(self, outStr):
        self.main_logger.info(outStr)

    def Warning(self, outStr):
        self.main_logger.warning(outStr)


log = SSLLogger()


def main():
    unittest.main()

if __name__ == '__main__':
    main()

