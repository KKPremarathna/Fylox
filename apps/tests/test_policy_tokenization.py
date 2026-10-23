import pytest

from backend.policies.service import tokenize


@pytest.mark.parametrize(
    ("singular", "plural"),
    [
        ("refund", "refunds"),
        ("return", "returns"),
        ("payment", "payments"),
        ("charge", "charges"),
        ("order", "orders"),
        ("policy", "policies"),
    ],
)
def test_supported_word_forms_share_tokens(
    singular,
    plural,
):
    assert tokenize(singular) == tokenize(plural)


def test_refund_and_return_remain_distinct():
    assert tokenize("refund") != tokenize("return")


def test_substrings_do_not_become_whole_word_matches():
    assert tokenize("charge").isdisjoint(
        tokenize("discharge")
    )