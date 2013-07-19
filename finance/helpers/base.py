#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

from finance import models


class Helper(object):
    """Helpers which manipulate transactions such as:

     * creating relationships between transactions,
     * add geocoding information,
     * fee association,
     * automatic categorization,
     * etc
    """

    def associate(self, a, b, relationship, **kw):
        return models.RelatedTransaction(trans_from=a, trans_to=b, type="A", relationship=relationship, **kw)

    def handle(self, account, transaction):
        return
