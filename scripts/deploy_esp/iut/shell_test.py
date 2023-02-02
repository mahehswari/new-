# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Unittests for shell.py file """

import getpass
import grp
import os
import pwd
import pytest
import iut.shell


pytestmark = pytest.mark.skip_ci('user/group data seems incorrect when run in pipeline')


class TestGetUserName:
    ''' Tests for get_user_name function '''

    def test_getting_user_name(self):
        ''' Check if get_user_name returns name current user '''

        assert iut.shell.get_user_name() == getpass.getuser()


class TestGetUserGroup:
    ''' Tests for get_user_group function '''

    def test_get_user_group(self):
        ''' Check if get_user_group returns group name current user '''

        user_id = pwd.getpwnam(getpass.getuser()).pw_gid
        group_name = grp.getgrgid(user_id).gr_name
        assert iut.shell.get_user_group() == group_name


class TestSetDirOwnership:
    ''' Tests for set_dir_ownership function '''

    TEST_USER = 'irc' # guaranteed to exist on ubuntu

    def user_id(self) -> int:
        ''' Get the UID of the test user '''
        return pwd.getpwnam(TestSetDirOwnership.TEST_USER).pw_gid

    def group_name(self) -> str:
        ''' Get the group name of the test user '''
        return grp.getgrgid(self.user_id()).gr_name

    def test_set_dir_ownership(self, tmp_path):
        ''' Check if set_dir_ownership set new owner for directory '''

        owner_before = tmp_path.owner()
        iut.shell.set_dir_ownership(str(tmp_path), TestSetDirOwnership.TEST_USER, self.group_name())
        owner_after = tmp_path.owner()

        iut.shell.set_dir_ownership(str(tmp_path), os.getlogin(), self.group_name())

        assert owner_before != owner_after
