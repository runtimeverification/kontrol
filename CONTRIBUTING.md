# Contributing to Kontrol

:+1::tada: Thanks for taking the time to contribute! :tada::+1:

The following is a set of guidelines for contributing to Kontrol. These are mostly guidelines, not rules. In each situation, use your best judgment, and feel free to propose changes to this document in a pull request.

## Opening a PR:
When opening a PR to Kontrol provide a description of what the PR is fixing/introducing. If you think it's helpful, you can also describe how you fix it. If the PR addresses an open issue, mention it in the description using a [Closing Keyword](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issuehttp:// "Closing Keyword"). Then:
  - Ask review from people with expertise in the fix/feature you addressed;
  - Assign yourself to the PR;
  - Link the Kontrol project to it;
  - If it is still a work in progress, `Create a draft pull request` and mark it as ready for review once you have finished. Otherwise, `Create a pull request`. 

### Make sure your changes pass on CI:
```
kup install k.openssl.procps --version v$(cat deps/k_release)
poetry install
poetry run kdist clean
CXX=clang++-14 poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.foundry
make format
make
make test
```
#### Update the expected output files
- If your changes involve updating the expected output files run:
```
make test TEST_ARGS="--numprocesses=4 --update-expected-output"
```

### Add a new test to CI:
  Usually, fixing an existent feature or creating a new one requires editing/adding a new test for it in CI:  `src/tests/integration/test_foundry_prove.py`
  - If you are adding a new feature, you might want to add a new test for it in CI (see the tests for recently added features like [test_deployment_summary](https://github.com/runtimeverification/kontrol/blob/0c18ea7e846f9278624007c8072326d1ea1f95df/src/tests/integration/test_foundry_prove.py#L603) and [test_xml_report](https://github.com/runtimeverification/kontrol/blob/0c18ea7e846f9278624007c8072326d1ea1f95df/src/tests/integration/test_foundry_prove.py#L743))
  - If you are addressing an issue that is reproducible with a Foundry test, then:
    - Add the test into `src/tests/integration/test-data/foundry/test`
    - Edit the `foundry-{prove-all,skip,fail}` lists according to your fix. For instance:
      - If the test was failing with `kontrol prove` and it is supposed to pass, then add the test to `foundry-prove-all` and make sure that the test is not in `foundry-prove-skip` (or `foundry-prove-skip-legacy` in case the test should also run in the legacy backend)
      - If the test was passing with `kontrol prove` and it is supposed to fail, then add the test to `foundry-fail` and make sure that the test is not in `foundry-prove-skip` (or `foundry-prove-skip-legacy` in case the test should also run in the legacy backend)
  - Run `make test-integration` locally to ensure all tests pass in CI.
  - Note: since `make test-integration` is time-expensive, before you can run your test to ensure it passes with: 
```
poetry run pytest src/tests/integration -k 'test_foundry_xml_report' --maxfail=1 --verbose --durations=0 --numprocesses=4 --dist=worksteal
```

### Run kontrol with a custom `pyk` / `kevm`
- If your fix involves changes in `pyk` or `kevm`, you might want to run Kontrol with a custom `pyk`/`kevm`. If that is the case, follow these [instructions](https://github.com/runtimeverification/kontrol/issues/319).
