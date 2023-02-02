# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)
"""Tests for iut.slo.system"""

import iut.slo.system
# pylint: disable=protected-access


class TestSystemClearPassword:
    """Test case for iut.slo.system.clear_passwords"""


    def test_no_password(self):
        """Test if clear_password does modify argv if there is no password defined"""

        original = ["--aaa", "aaa", "-p", "ccc", "--xxx=hghd"]
        cleared = iut.slo.system.clear_password(original)

        assert original is not cleared
        assert original == cleared


    def test_empty_argv(self):
        """Test if clear_passwords works with empty argv"""

        original = []
        cleared = iut.slo.system.clear_password(original)

        assert original is not cleared
        assert original == cleared


    def test_ta_password(self):
        """Tests two arguments password version"""

        password = "xxxxa"
        original = ["a", "aaa", "--git-password", password, "ccc"]
        cleared = iut.slo.system.clear_password(original)

        assert original[:3] + [iut.slo.system._REPLACEMENT] + original[4:] == cleared


    def test_ta_password_first(self):
        """Test clear_pasword when two argument password is first in argv"""

        password = "xxxxa"
        original = ["--git-password", password, "aaaasss", "arerte"]
        cleared = iut.slo.system.clear_password(original)

        assert original[:1] + [iut.slo.system._REPLACEMENT] + original[2:] == cleared


    def test_ta_password_last(self):
        """Test clear_password when two argument password is last in argv"""

        password = "xxxxa"
        original = ["a", "aaa", "--git-password", password]
        cleared = iut.slo.system.clear_password(original)

        assert original[:3] + [iut.slo.system._REPLACEMENT] == cleared


    def test_sa_password(self):
        """Tests clear_password when argv contains only single argument password"""

        password = "--git-password=xxxxa"
        original = ["a", "aaa", password, "ccc"]
        cleared = iut.slo.system.clear_password(original)

        expected = f"--git-password={iut.slo.system._REPLACEMENT}"
        assert original[:2] + [expected] + original[3:] == cleared


    def test_sa_password_first(self):
        """Test clear_passwords when single argument password is first in argv"""

        password = "--git-password=xxxxa"
        original = [password, "aaaasss", "arerte"]
        cleared = iut.slo.system.clear_password(original)

        expected = f"--git-password={iut.slo.system._REPLACEMENT}"
        assert [expected] + original[1:] == cleared


    def test_sa_password_last(self):
        """Test clear_password when single argument password is last in argv"""

        password = "--git-password=xxxxa"
        original = ["a", "aaa", password]
        cleared = iut.slo.system.clear_password(original)

        expected = f"--git-password={iut.slo.system._REPLACEMENT}"
        assert original[:2] + [expected] == cleared


    def test_sa_password_custom_arg_and_custom_replacement(self):
        """Test clear_password with single argument password and custom argument name and custom replacement text"""

        custom = "--xxxa"
        password = "--xxxa=apasshere%$^"
        replacement = "custom"
        original = ["a", "aaa", password, "aaddd"]

        cleared = iut.slo.system.clear_password(original, clear=[custom], replacement=replacement)

        expected = f"--xxxa={replacement}"
        assert original[:2] + [expected] + original[3:] == cleared
