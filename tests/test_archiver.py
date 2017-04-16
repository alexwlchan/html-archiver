#!/usr/bin/env python
# -*- encoding: utf-8

import glob
import os

import pytest


def test_cases():
    return [
        p[len('inputs/'):]
        for p in glob.glob('inputs/*.html') + glob.glob('inputs/**/*.html')
    ]


@pytest.mark.parametrize('input_path', test_cases())
def test_archiver_is_correct(archiver, input_path):
    url = 'file:///%s' % input_path
    out = 'expected/%s.html' % os.path.splitext(input_path)[0]

    assert archiver.archive_url(url) == open(out).read()
