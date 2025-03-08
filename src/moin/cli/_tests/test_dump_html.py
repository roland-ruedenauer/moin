# Copyright: 2025 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.cli.maint.dump_html tests
"""

from moin.cli._tests import assert_p_succcess, get_html_dump_path


def test_dump_html(dump_html):
    assert_p_succcess(dump_html)
    assert get_html_dump_path().exists()
