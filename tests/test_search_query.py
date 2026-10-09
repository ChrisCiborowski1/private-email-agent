import pytest

from private_email_agent.search_query import build_gmail_query


def test_builds_merchant_purchase_date_query():
    assert build_gmail_query(
        merchant="Banana Republic",
        intent="purchase",
        after="2026-09-20",
        before="2026-10-01",
    ) == (
        '"Banana Republic" category:purchases '
        "after:2026/09/20 before:2026/10/01"
    )


def test_combines_discovered_domain_and_advanced_refinement():
    assert build_gmail_query(
        sender_domain="mail.example.com",
        gmail_query='subject:(receipt OR shipped)',
    ) == 'from:mail.example.com subject:(receipt OR shipped)'


@pytest.mark.parametrize(
    "value",
    ["banana republic", "@example.com", "example", "example.com OR spam"],
)
def test_rejects_invalid_sender_domain(value):
    with pytest.raises(ValueError, match="sender_domain"):
        build_gmail_query(sender_domain=value)


def test_rejects_reversed_date_range():
    with pytest.raises(ValueError, match="before must be later"):
        build_gmail_query(after="2026-10-01", before="2026-09-20")
