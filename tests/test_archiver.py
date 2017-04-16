#!/usr/bin/env python
# -*- encoding: utf-8

import glob
import os

import pytest


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_DIR, 'inputs')
EXPECTED_DIR = os.path.join(TEST_DIR, 'expected')


def test_cases():
    return [
        p[len('%s/' % INPUT_DIR):]
        for p in (glob.glob('%s/*.html' % INPUT_DIR) +
                  glob.glob('%s/**/*.html' % INPUT_DIR))
    ]


@pytest.mark.parametrize('input_path', test_cases())
def test_archiver_is_correct(archiver, input_path):
    url = 'file:///%s' % input_path
    out = '%s/%s.html' % (EXPECTED_DIR, os.path.splitext(input_path)[0])

    assert archiver.archive_url(url) == open(out).read()
