#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import sslconfig



sslConfig = SSLConfig("/etc/sysconfig/gd-ssl-config.conf")
#log = SSLLogger(sslconfig.sslConfig.logFilename, sslconfig.sslConfig.logLevel)


def main():
    unittest.main()

if __name__ == '__main__':
    main()

