import pytest
import mt940


@pytest.fixture
def sta_data():
    with open('tests/jejik/abnamro.sta') as fh:
        return fh.read()


def test_pre_processor(sta_data):
    transactions = mt940.models.Transactions(processors=dict(
        pre_closing_balance=[
            mt940.processors.add_currency_pre_processor('USD'),
        ],
        pre_opening_balance=[
            mt940.processors.add_currency_pre_processor('EUR'),
        ],
    ))

    transactions.parse(sta_data)
    assert transactions.data['closing_balance'].amount.currency == 'USD'
    assert transactions.data['opening_balance'].amount.currency == 'EUR'


def test_post_processor(sta_data):
    transactions = mt940.models.Transactions(processors=dict(
        post_closing_balance=[
            mt940.processors.date_cleanup_post_processor,
        ],
    ))

    transactions.parse(sta_data)
    assert 'closing_balance_day' not in transactions.data


