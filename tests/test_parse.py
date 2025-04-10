import io
import json
from datetime import date

import pytest
from bs4 import BeautifulSoup

from ixbrlparse import IXBRL
from ixbrlparse.core import ixbrlContext, ixbrlNonNumeric, ixbrlNumeric

TEST_ACCOUNTS = [
    "tests/test_accounts/account_1.html",
    "tests/test_accounts/account_2.html",
    "tests/test_accounts/account_3.html",
    "tests/test_accounts/account_4.html",
    "tests/test_accounts/account_5.html",
    "tests/test_accounts/account_errors.html",
]
TEST_XML_ACCOUNTS = [
    "tests/test_accounts/account_1.xml",
]

EXPECTED_TABLE_KEYS = [
    "schema",
    "name",
    "value",
    "unit",
    "instant",
    "startdate",
    "enddate",
]


def test_open():
    with open(TEST_ACCOUNTS[0]) as a:
        x = IXBRL(a)
        assert x.filetype == "ixbrl"
        assert isinstance(x.soup, BeautifulSoup)

    x = IXBRL.open(TEST_ACCOUNTS[1])
    assert x.filetype == "ixbrl"
    assert isinstance(x.soup, BeautifulSoup)


def test_open_str():
    with open(TEST_ACCOUNTS[0]) as a:
        content = a.read()
        x = IXBRL(io.StringIO(content))
        assert x.filetype == "ixbrl"
        assert isinstance(x.soup, BeautifulSoup)


def test_open_xml():
    with open(TEST_XML_ACCOUNTS[0]) as a:
        x = IXBRL(a)
        assert x.filetype == "xbrl"
        assert isinstance(x.soup, BeautifulSoup)

    x = IXBRL.open(TEST_XML_ACCOUNTS[0])
    assert x.filetype == "xbrl"
    assert isinstance(x.soup, BeautifulSoup)


def test_open_xml_str():
    with open(TEST_XML_ACCOUNTS[0]) as a:
        content = a.read()
        x = IXBRL(io.StringIO(content))
        assert x.filetype == "xbrl"
        assert isinstance(x.soup, BeautifulSoup)


@pytest.mark.parametrize(
    "account,schema,namespaces",
    zip(
        TEST_ACCOUNTS[0:5] + TEST_XML_ACCOUNTS,
        [
            "https://xbrl.frc.org.uk/FRS-102/2014-09-01/FRS-102-2014-09-01.xsd",
            "http://www.xbrl.org/uk/gaap/core/2009-09-01/uk-gaap-full-2009-09-01.xsd",
            "http://www.xbrl.org/uk/gaap/core/2009-09-01/uk-gaap-full-2009-09-01.xsd",
            "https://xbrl.frc.org.uk/FRS-102/2014-09-01/FRS-102-2014-09-01.xsd",
            "https://xbrl.frc.org.uk/FRS-102/2014-09-01/FRS-102-2014-09-01.xsd",
            "http://www.companieshouse.gov.uk/ef/xbrl/uk/fr/gaap/ae/2009-06-21/uk-gaap-ae-2009-06-21.xsd",
        ],
        [
            11,
            12,
            12,
            38,
            19,
            10,
        ],
    ),
)
def test_schema(account, schema, namespaces):
    x = IXBRL.open(account)
    assert x.schema == schema
    assert len(x.namespaces) == namespaces


@pytest.mark.parametrize(
    "account,contexts,expected_key",
    [(TEST_ACCOUNTS[0], 12, "dcur6"), (TEST_XML_ACCOUNTS[0], 6, "y2")],
)
def test_contexts(account, contexts, expected_key):
    x = IXBRL.open(account)

    # test all the contexts have been found
    assert len(x.contexts) == contexts

    # test that the context is correct class
    assert isinstance(list(x.contexts.values())[0], ixbrlContext)

    # test an expected key is in the contexts
    assert expected_key in x.contexts


def test_contexts_values():
    x = IXBRL.open(TEST_ACCOUNTS[0])

    # test values have been correctly parsed
    assert x.contexts["icur1"].instant == date(2017, 10, 31)
    assert x.contexts["dcur1"].startdate == date(2016, 11, 1)
    assert x.contexts["dcur1"].enddate == date(2017, 10, 31)
    assert x.contexts["dcur1"].entity["identifier"] == "02345678"
    assert x.contexts["dcur1"].entity["scheme"] == "http://www.companieshouse.gov.uk/"


def test_contexts_segments():
    x = IXBRL.open(TEST_ACCOUNTS[0])

    assert len(x.contexts["dcur6"].segments) == 1
    assert x.contexts["dcur6"].segments[0]["tag"] in "xbrldi:explicitMember"
    assert x.contexts["dcur6"].segments[0]["value"] == "uk-bus:FullAccounts"
    assert (
        x.contexts["dcur6"].segments[0].get("dimension")
        == "uk-bus:AccountsTypeDimension"
    )


def test_contexts_values_xml():
    x = IXBRL.open(TEST_XML_ACCOUNTS[0])

    # test values have been correctly parsed
    assert x.contexts["s1"].instant == date(2020, 1, 1)
    assert x.contexts["y1"].startdate == date(2020, 1, 1)
    assert x.contexts["y1"].enddate == date(2020, 12, 31)
    assert x.contexts["y1"].entity["identifier"].strip() == "DEMO XML LIMITED"
    assert x.contexts["y1"].entity["scheme"] == "gee-lawson-/results"


# def test_contexts_segments_xml():
#     x = IXBRL.open(TEST_XML_ACCOUNTS[0])

#     assert len(x.contexts["dcur6"].segments) == 1
#     assert x.contexts["dcur6"].segments[0]["tag"] in "xbrldi:explicitMember"
#     assert x.contexts["dcur6"].segments[0]["value"] == "uk-bus:FullAccounts"
#     assert (
#         x.contexts["dcur6"].segments[0].get("dimension")
#         == "uk-bus:AccountsTypeDimension"
#     )


def test_contexts_no_prefix():
    # check an account with <context> elements (without prefix)
    x = IXBRL.open(TEST_ACCOUNTS[1])

    # test values have been correctly parsed
    assert x.contexts["current-period-director2"].startdate == date(2016, 4, 1)
    assert x.contexts["current-period-director2"].enddate == date(2017, 3, 31)
    assert x.contexts["current-period-director2"].entity["identifier"] == "12345678"
    assert (
        x.contexts["current-period-director2"].entity["scheme"]
        == "http://www.companieshouse.gov.uk/"
    )


@pytest.mark.parametrize("account", [a for a in TEST_ACCOUNTS if "error" not in a])
def test_json(account):
    x = IXBRL.open(account)
    x.to_json()

    assert json.dumps(x.to_json())


def test_units():
    x = IXBRL.open(TEST_ACCOUNTS[0])

    assert len(x.units) == 1
    assert x.units["GBP"] == "iso4217:GBP"


def test_units_no_prefix():
    x = IXBRL.open(TEST_ACCOUNTS[1])

    assert len(x.units) == 2
    assert x.units["currencyUnit"] == "iso4217:GBP"
    assert x.units["shares"] == "shares"


def test_nonnumeric():
    x = IXBRL.open(TEST_ACCOUNTS[2])

    assert len(x.nonnumeric) == 15
    assert isinstance(x.nonnumeric[0], ixbrlNonNumeric)
    assert "FAKETEST TECHNOLOGIES LIMITED" in [n.value for n in x.nonnumeric]
    for n in x.nonnumeric:
        if (
            n.schema == "uk-gaap-cd-bus"
            and n.name == "UKCompaniesHouseRegisteredNumber"
        ):
            assert n.value == "03456789"
            assert isinstance(n.context, ixbrlContext)


def test_nonnumeric_xml():
    x = IXBRL.open(TEST_XML_ACCOUNTS[0])

    assert len(x.nonnumeric) == 14
    assert isinstance(x.nonnumeric[0], ixbrlNonNumeric)
    assert "DEMO XML LIMITED" in [n.value for n in x.nonnumeric]
    for n in x.nonnumeric:
        if n.name == "NameApprovingDirector":
            assert n.value == "JOAN IMAGINARYNAME"
            assert isinstance(n.context, ixbrlContext)


def test_numeric():
    x = IXBRL.open(TEST_ACCOUNTS[3])

    assert len(x.numeric) == 32
    for n in x.numeric:
        assert isinstance(n, ixbrlNumeric)

        if (
            n.name == "NetCurrentAssetsLiabilities"
            and n.context.id == "cfwd_31_03_2017"
        ):
            assert n.format.sign == "-"
            assert n.value == -17957

        if n.format.sign == "-":
            assert n.value < 0

    assert x.numeric[0].unit == "iso4217:GBP"
    assert x.numeric[0].value == 52982
    assert x.numeric[0].name == "PropertyPlantEquipment"
    assert x.numeric[0].schema == "ns5"


def test_numeric_xml():
    x = IXBRL.open(TEST_XML_ACCOUNTS[0])

    assert len(x.numeric) == 13
    for n in x.numeric:
        assert isinstance(n, ixbrlNumeric)

        if n.name == "NumberOrdinarySharesAllotted" and n.context.id == "e2":
            assert n.format.sign == ""
            assert n.value == 1

        if n.format.sign == "-":
            assert n.value < 0

    assert x.numeric[0].unit == "iso4217:GBP"
    assert x.numeric[0].value == 1
    assert x.numeric[0].name == "CashBankInHand"
    assert x.numeric[0].schema == "unknown"


def test_table_output():
    x = IXBRL.open(TEST_ACCOUNTS[1])
    table = x.to_table("all")

    assert len(table) == 27

    for row in table[0:5]:
        for col, value in row.items():
            # output is two dimensional
            assert not isinstance(value, (list, dict, tuple))

            # column is expected
            assert col in EXPECTED_TABLE_KEYS or col.startswith("segment")

        # needs either an instant or start & end dates
        assert row["instant"] or (row["startdate"] and row["enddate"])


def test_table_output_numeric():
    x = IXBRL.open(TEST_ACCOUNTS[2])
    table = x.to_table("numeric")

    assert len(table) == 18

    for row in table[0:5]:
        for col, value in row.items():
            # output is two dimensional
            assert not isinstance(value, (list, dict, tuple))

            # column is expected
            assert col in EXPECTED_TABLE_KEYS or col.startswith("segment")

        # value is numeric
        assert isinstance(row["value"], (int, float))


def test_table_output_nonnumeric():
    x = IXBRL.open(TEST_ACCOUNTS[3])
    table = x.to_table("nonnumeric")

    assert len(table) == 59

    for row in table[0:5]:
        for col, value in row.items():
            # output is two dimensional
            assert not isinstance(value, (list, dict, tuple))

            # column is expected
            assert col in EXPECTED_TABLE_KEYS or col.startswith("segment")

        # value is a string
        assert isinstance(row["value"], (str, type(None)))


def test_errors_raised():
    with open(TEST_ACCOUNTS[5]) as a:
        with pytest.raises(NotImplementedError):
            IXBRL(a)

    with open(TEST_ACCOUNTS[5]) as a:
        x = IXBRL(a, raise_on_error=False)
        assert isinstance(x.soup, BeautifulSoup)
        assert len(x.errors) == 1


def test_errors_raised_open():
    with pytest.raises(NotImplementedError):
        IXBRL.open(TEST_ACCOUNTS[5])

    x = IXBRL.open(TEST_ACCOUNTS[5], raise_on_error=False)
    assert isinstance(x.soup, BeautifulSoup)
    assert len(x.errors) == 1
