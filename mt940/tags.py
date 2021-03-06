# vim: fileencoding=utf-8:
'''

Format
---------------------

Sources:

.. _Swift for corporates: http://www.sepaforcorporates.com/\
    swift-for-corporates/account-statement-mt940-file-format-overview/
.. _Rabobank MT940: https://www.rabobank.nl/images/\
    formaatbeschrijving_swift_bt940s_1_0_nl_rib_29539296.pdf

 - `Swift for corporates`_
 - `Rabobank MT940`_

::

    [] = optional
    ! = fixed length
    a = Text
    x = Alphanumeric, seems more like text actually. Can include special
        characters (slashes) and whitespace as well as letters and numbers
    d = Numeric separated by decimal (usually comma)
    c = Code list value
    n = Numeric
'''
import re
import enum
import logging

import mt940


logger = logging.getLogger(__name__)


class Tag(object):
    id = 0
    scope = mt940.models.Transactions

    def __init__(self):
        self.re = re.compile(self.pattern, re.IGNORECASE | re.VERBOSE)

    def parse(self, transactions, value):
        logger.debug('matching (%d) %r against %r', len(value), value,
                     self.pattern)
        match = self.re.match(value)
        assert match is not None, 'Unable to parse %r from %r' % (self, value)
        return match.groupdict()

    def __call__(self, transactions, value):
        return value

    def __new__(cls, *args, **kwargs):
        cls.name = cls.__name__

        words = re.findall('([A-Z][a-z]+)', cls.__name__)
        cls.slug = '_'.join(w.lower() for w in words)

        return object.__new__(cls, *args, **kwargs)

    def __hash__(self):
        return self.id


class TransactionReferenceNumber(Tag):
    '''Transaction reference number

    Pattern: 16x
    '''
    id = 20
    pattern = r'(?P<transaction_reference>.{0,16})'


class RelatedReference(Tag):
    '''Related reference

    Pattern: 16x
    '''
    id = 21
    pattern = r'(?P<related_reference>.{0,16})'


class AccountIdentification(Tag):
    '''Account identification

    Pattern: 35x
    '''
    id = 25
    pattern = r'(?P<account_identification>.{0,35})'


class StatementNumber(Tag):
    '''Statement number / sequence number

    Pattern: 5n[/5n]
    '''
    id = 28
    pattern = r'''
    (?P<statement_number>\d{1,5})  # 5n
    (?:/(?P<sequence_number>\d{1,5}))?  # [/5n]
    '''


class BalanceBase(Tag):
    '''Balance base

    Pattern: 1!a6!n3!a15d
    '''
    pattern = r'''^
    (?P<status>[DC])  # 1!a Debit/Credit
    (?P<year>\d{2})  # 6!n Value Date (YYMMDD)
    (?P<month>\d{2})
    (?P<day>\d{2})
    (?P<currency>.{3})  # 3!a Currency
    (?P<amount>[0-9,]{0,16})  # 15d Amount (includes decimal sign, so 16)
    '''

    def __call__(self, transactions, value):
        data = super(BalanceBase, self).__call__(transactions, value)
        data['amount'] = mt940.models.Amount(**data)
        data['date'] = mt940.models.Date(**data)
        return {
            self.slug: mt940.models.Balance(**data)
        }


class OpeningBalance(BalanceBase):
    id = 60


class Statement(Tag):
    '''Statement

    Pattern: 6!n[4!n]2a[1!a]15d1!a3!c16x[//16x]
    '''
    id = 61
    scope = mt940.models.Transaction
    pattern = r'''^
    (?P<year>\d{2})  # 6!n Value Date (YYMMDD)
    (?P<month>\d{2})
    (?P<day>\d{2})
    (?P<entry_month>\d{2})?  # [4!n] Entry Date (MMDD)
    (?P<entry_day>\d{2})?
    (?P<status>[A-Z]?[DC])  # 2a Debit/Credit Mark
    (?P<funds_code>[A-Z])? # [1!a] Funds Code (3rd character of the currency
                            # code, if needed)
    (?P<amount>[\d,]{1,15})  # 15d Amount
    (?P<id>[A-Z][A-Z0-9]{3})?  # 1!a3!c Transaction Type Identification Code
    (?P<customer_reference>.{0,16})  # 16x Customer Reference
    (//(?P<bank_reference>.{0,16}))?  # [//16x] Bank Reference
    (?P<extra_details>.{0,34})  # [34x] Supplementary Details (this will be on
                                # a new/separate line)
    '''

    def __call__(self, transactions, value):
        data = super(Statement, self).__call__(transactions, value)
        data.setdefault('currency', transactions.currency)

        data['amount'] = mt940.models.Amount(**data)
        data['date'] = mt940.models.Date(**data)

        if data.get('entry_day') and data.get('entry_month'):
            data['entry_date'] = mt940.models.Date(
                day=data.get('entry_day'),
                month=data.get('entry_month'),
                year=str(data['date'].year),
            )
        return data


class ClosingBalance(BalanceBase):
    id = 62


class AvailableBalance(BalanceBase):
    id = 64


class ForwardAvailableBalance(BalanceBase):
    id = 65


class TransactionDetails(Tag):
    '''Transaction details

    Pattern: 6x65x
    '''
    id = 86
    scope = mt940.models.Transaction
    pattern = r'(?P<transaction_details>[\s\S]{0,330})'


@enum.unique
class Tags(enum.Enum):
    TRANSACTION_REFERENCE_NUMBER = TransactionReferenceNumber()
    RELATED_REFERENCE = RelatedReference()
    ACCOUNT_IDENTIFICATION = AccountIdentification()
    STATEMENT_NUMBER = StatementNumber()
    OPENING_BALANCE = OpeningBalance()
    STATEMENT = Statement()
    CLOSING_BALANCE = ClosingBalance()
    AVAILABLE_BALANCE = AvailableBalance()
    FORWARD_AVAILABLE_BALANCE = ForwardAvailableBalance()
    TRANSACTION_DETAILS = TransactionDetails()


TAG_BY_ID = {t.value.id: t.value for t in Tags}



