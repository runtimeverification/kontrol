#!/usr/bin/env bash

set -euxo pipefail

which kontrol
kontrol --help
kontrol version

cd test-project
kontrol build
kontrol prove --match-test 'AssertTest.test_assert_true()'
