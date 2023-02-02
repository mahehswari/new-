# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" Helper functions and fixtures for testing with pytest """

import os
from pathlib import Path
import random
import string
from typing import Iterator
import pytest


@pytest.fixture(autouse=True)
def tmp_path(tmp_path) -> Iterator[Path]: # pylint: disable=redefined-outer-name # (fixture redefinition)
    """ Fixture that provides a fresh temporary directory and cd-s into it

        This (moral equivalent of) cwd randomization is essential to achieve reproducibility/side-effectlessness.
        It is for this reason that this fixture is marked as autouse.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old_cwd)


def repo_root() -> Path:
    """ Return the root directory of this git repository. """
    return Path(__file__).parents[2]


def random_identifier(*, length: int = 10) -> str:
    """ Generate a simple (pseudo)random identifier like `oomsylatxa` """
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def random_ipv4() -> str:
    """ Generate a (pseudo)random IPv4 address string """
    return '.'.join(str(random.randrange(256)) for _ in range(4))


def random_mac(*, delimiter: str = '-', bits: int = 48) -> str:
    """ Generate a (pseudo)random MAC address string """
    return delimiter.join(hex(random.randrange(0x100)) for _ in range(bits // 8))
