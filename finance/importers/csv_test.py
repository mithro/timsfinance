#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

from django.utils import unittest


class CSVTestCase(unittest.TestCase):
    def setUp(self):
        # Create an account


    def test_unique(self):
        # Test csv which has a unique identifer....


    def test_multi(self):
        # -----------------
        csv_basic = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        # -----------------
        # Import the exact same data twice, should cause change


        # -----------------
        csv_basic1 = """\
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        csv_basic2 = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
"""

        # -----------------
        csv_duplicates = """\
16/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
15/11/2011,"-0.20","INTNL TRANSACTION FEE",""
14/11/2011,"-0.20","INTNL TRANSACTION FEE",""
"""


        # -----------------
        csv_missing_a = """\
10/11/2011,"0.20","Transaction D",""
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""

        csv_missing_a = """\
10/11/2011,"0.20","Transaction D",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        # -----------------
        csv_middle_addition_a = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""

        csv_middle_addition_b = """\
09/11/2011,"0.20","Transaction C",""
09/11/2011,"0.20","Transaction D",""
09/11/2011,"0.20","Transaction B",""
09/11/2011,"0.20","Transaction A",""
"""
        # -----------------

    def test_running_total(self):
        csv_normal1 = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
"""
        csv_normal2 = """\
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running_missing = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running_extra = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""
        # -----------------
        csv_running_wrong_order = """\
,01/02/2012,REWARD BENEFIT VISA (OS) ,0.10,22672.03
,01/02/2012,REWARD BENEFIT BPAY ,0.30,22671.78
,01/02/2012,REWARD BENEFIT VISA (LOCAL) ,0.15,22671.93
,31/01/2012,NON REDIATM WITHDRAWAL FEE ,-0.50,22671.48
"""

