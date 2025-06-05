# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import unittest
from unittest.suite import BaseTestSuite

from django.conf import settings
from django.test.runner import DiscoverRunner


class PartialTestLoader(unittest.TestLoader):
    def _recursive_filter(self, tests, node_index, node_total):
        if len(tests._tests):
            if isinstance(tests._tests[0], BaseTestSuite):
                for suite in tests._tests:
                    self._recursive_filter(suite, node_index, node_total)
            else:
                tests._tests = sorted(tests._tests, key=lambda x: f"{x.__class__.__module__}.{x.__class__.__name__}")
                tests._tests = tests._tests[node_index - 1 :: node_total]

    def discover(self, *args, **kwargs) -> unittest.suite.TestSuite:
        tests = super().discover(*args, **kwargs)

        node_total = int(os.environ.get("CI_NODE_TOTAL", 1))
        node_index = int(os.environ.get("CI_NODE_INDEX", 1))

        sys.stderr.write("\n")
        sys.stderr.write("=" * 100)
        sys.stderr.write(f"\nNode {node_index} of {node_total}\n")
        sys.stderr.write("=" * 100)
        sys.stderr.write("\n")

        if node_total > 1:
            self._recursive_filter(tests, node_index, node_total)

        return tests


class SuiteRunner(DiscoverRunner):
    test_loader = PartialTestLoader()

    # Copyright Travis Jensen
    # Copied from https://stackoverflow.com/questions/4088253/django-how-to-detect-test-environment-check-determine-if-tests-are-being-ru/7651002#7651002
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings.TEST_MODE = True

        # Force settings.DEBUG to True
        # Since tests depend on it
        self.debug_mode = True
