#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

def dollar_fmt(number, currency=None):
    u"""Formats a number (in cents) as dollars.

    Args:
        number: The number to format.
        currency: The symbol to use at the beginning, defaults to $.

    >>> dollar_fmt(1)
    '$+0.01'

    >>> dollar_fmt(100)
    '$+1.00'

    >>> dollar_fmt(100000)
    '$+1,000.00'

    >>> dollar_fmt(100059)
    '$+1,000.59'

    >>> dollar_fmt(-1)
    '$-0.01'

    >>> dollar_fmt(-100)
    '$-1.00'

    >>> dollar_fmt(-100000)
    '$-1,000.00'

    >>> dollar_fmt(-100059)
    '$-1,000.59'

    >>> dollar_fmt(120, currency=u"£")
    u'\\xa3+1.20'

    >>> dollar_fmt(499, currency=u"€")
    u'\\u20ac+4.99'
    """
    if currency is None:
        currency = "$"

    number = str(number)
    if number[0] == "-":
        sign = "-"
        number = number[1:]
    else:
        sign = "+"

    cents = number[-2:]
    while len(cents) < 2:
        cents = "0" + cents

    dollars = list(number[:-2])

    bits = [""]
    while len(dollars) > 0:
        if len(bits[0]) == 3:
            bits.insert(0, "")
        bits[0] = dollars.pop(-1)+bits[0]

    if bits[0] == "":
        bits[0] = "0"

    return currency+sign+",".join(bits)+'.'+cents


def dollar_display(description, field_amount, field_currency):
    u"""Display a field on a model using the dollar_fmt above.

    Args:
        description: The description of the field.
        field_amount: The field which contains the amount.
        field_currency: The field which contains the currency symbol.

    >>> class Test:
    ...   amount = 1200
    ...   currency = u"£"
    >>> f = dollar_display("Description", "amount", "currency")
    >>> f(Test)
    u'\\xa3+12.00'
    >>>

    """
    def f(obj):
        value = eval("obj.%s" % field_amount)
        currency = eval("obj.%s" % field_currency)
        if value is not None:
            return dollar_fmt(value, currency)
        return "(None)"
    f.short_description = description
    return f

if __name__ == "__main__":
    import doctest
    doctest.testmod()
