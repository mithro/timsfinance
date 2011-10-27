
import re
import os
import unittest
import doctest

from finance.importers import commbank_test
import finance.utils



def suite():
    mylocation = os.path.dirname(__file__)

    suite = unittest.TestSuite()
    for dirpath, dirnames, filenames in os.walk(mylocation):
        for filename in filenames:
           remaining = dirpath[len(os.path.commonprefix([mylocation, dirpath])):].replace('/', '.')
           test = "finance%s.%s" % (remaining, filename[:-3])

           # Unittest test
           if filename.endswith('_test.py'):
               suite.addTest(unittest.TestLoader().loadTestsFromName(test))

           # Docutil test
           if filename.endswith('.py'):
               if re.search('>>>', file(os.path.join(dirpath, filename)).read()):
                   suite.addTest(doctest.DocTestSuite(finance.utils))


    return suite
