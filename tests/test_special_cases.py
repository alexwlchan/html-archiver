# -*- encoding: utf-8
"""
This test makes requests to real web pages (or rather, betamax copies
of them) and tests the archiver behaviour.
"""


def test_marco_org_encoding_is_correct(betamax_archiver):
    """
    Test that the encoding is inferred correctly on marco.org.

    There was a bug (#15) where the page was read as Latin-1, even though
    the page had a <meta> tag specifying a UTF-8 charset.  This meant the
    permalink wouldn't render as an infinity-symbol, but as special chars.
    Check we do it correctly.
    """
    html = betamax_archiver.archive_url('https://marco.org/2017/04/15/mac-pro-audacity-of-yes')  # noqa
    assert u'∞' in html
