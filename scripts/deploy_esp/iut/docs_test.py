# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Unittests file for docs.py """

from argparse import Namespace
from pathlib import Path
import os
from typing import Iterator
import pytest
import conftest
import iut.docs

class TestBuildOfflineDocs:
    ''' Tests for build_offline_docs function '''

    @pytest.fixture
    def mock_docs_dir(self, tmp_path) -> Iterator[Path]:
        ''' Create a fake docs/ subdirectory and write a shim python file in it. Return its subpath '''
        docs_path = tmp_path / conftest.random_identifier()
        docs_path.mkdir()
        test_argv_script = (
            '#!/usr/bin/env python3\n'
            'import sys\n'
            f'with open({repr(str(docs_path / "stdout"))}, "w") as stdout:\n'
            '    stdout.write("\\n".join(sys.argv))\n')

        with open(docs_path / 'generate_docs.py', 'w', encoding="utf-8") as generate_docs:
            generate_docs.write(test_argv_script)
            os.chmod(generate_docs.fileno(), 0o555)

        yield docs_path

    def test_build_offline_docs(self, tmp_path, mock_docs_dir, caplog):
        ''' Test run function build_offline_docs '''

        toolchain_cfg = {
            'docs': {
                'url': 'https://github.com/docker/compose',
                'branch': 'v2',
                'path': str(mock_docs_dir) },
            'path': {
                'part': {
                    'package': {
                        'docs': str(mock_docs_dir) }},
                'full': {
                    'toolchain': str(mock_docs_dir),
                    'repo': '' }}}

        with caplog.at_level('INFO'):
            iut.docs.build_offline_docs(
                args=Namespace(git_user=None, git_password=None, debug=False),
                toolchain_cfg=toolchain_cfg,
                output_root=str(tmp_path / conftest.random_identifier()),
                tmp_root=str(tmp_path / conftest.random_identifier()))

        assert caplog.records[0].getMessage() == "Successfully generated the offline documentation package"
