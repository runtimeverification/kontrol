---
copyright: Copyright (c) Runtime Verification, Inc. All Rights Reserved.
---

# Kontrol Contributor Guide

Thank you for making a contribution to Kontrol.
The following is a set of guidelines to get your changes reviewed, tested and merged into Kontrol. If you have any questions about this process or Kontrol in general, please get in touch via our [Discord Server](https://discord.com/invite/CurfmXNtbN).

## Opening an issue

If you are using Kontrol and want to report something that doesn't work as you expect, the best way to do so is to open an issue against the [Kontrol repository](https://github.com/runtimeverification/kontrol).
Please make sure to include as much relevant information as possible in your issue to help us reproduce it. We will reply to you with any questions we have about the issue, then triage it to get fixed.

## Making a change to Kontrol

We welcome contributions to Kontrol from the community. Because running the Kontrol test suite uses our private compute resources, there are a few steps to go through to get your changes tested and merged.

### Fork the Kontrol repository

For external contributors, please [fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) the Kontrol repository following the Github documentation. Commit any changes you make to a branch on your fork.

### Develop your changes locally

The first step is to develop and test your changes locally.

##### 1. Build Kontrol from source
```
kup install k.openssl.procps --version v$(cat deps/k_release)
kup install k.openssl.procps.secp256k1 --version v$(cat deps/k_release)
poetry install
poetry run kdist clean
CXX=clang++-14 poetry run kdist --verbose build -j2 evm-semantics.haskell kontrol.foundry
```
(see more detailed instructions [here](https://github.com/runtimeverification/kontrol?tab=readme-ov-file#build-from-source))

##### 2. Ensure the Code Quality Checks
```
make check
make format
```
##### 3. Ensure the tests pass
```
make test
```
- If your changes involve updating the expected output files, run:
```
make test TEST_ARGS="--update-expected-output"
```

If your changes only apply to documentation, you can skip the testing phase.

### Open a PR:
When submitting a PR to Kontrol, provide a description of what the PR is fixing/introducing. If you think it's helpful, please describe the implementation for the fix or a new feature in more detail. If the PR addresses an open issue, mention it in the description using a [Closing Keyword](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue). Then:
  - Request a review from people with expertise in the fix/feature you introduced. If you are still determining whom to request a review from, please check the last contributors to the edited files;
  - Assign yourself to the PR;
  - In the Projects tab, select "Kontrol" to link the PR with the Kontrol project;
  - If it is still a work in progress, `Create a draft pull request` and mark it as ready for review once you have finished. Otherwise, `Create a pull request`. 

#### External contributors
Once you have tested your changes locally, push your commits to your fork of Kontrol and [open a pull request (PR)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests), again following the Github documentation. Because this PR is coming from an external fork, the Kontrol test suite and CI process will not run. This is expected behaviour. Additionally, please make sure that the commit history in your PR is clean by [rebasing](https://docs.github.com/en/get-started/using-git/about-git-rebase) any messy or partial commits. Finally, it is important that your commits are based on the Kontrol `master` branch.

Next, please request a review from a Kontrol maintainer on your PR. The last person to modify the files you are changing is a good start, or if you're not sure, tag [@palinatolmach](https://github.com/palinatolmach) as a fallback.

Once your code has been reviewed by a Kontrol maintainer, we will open a new PR that includes your commits with proper attribution. Doing so allows us to run our internal CI processes once we are happy with your code. If the tests pass, we will merge the PR and close your original PR. If changes need to be made subsequently to get tests to pass, they will need to be pushed to your original fork branch.

### Licensing

Kontrol is licensed under the [BSD 3-Clause License](https://github.com/runtimeverification/kontrol/blob/master/LICENSE). If you make changes to Kontrol via a pull request, your changes will automatically be licensed under the same license following [Github's terms of service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#6-contributions-under-repository-license).

### Contribution guidance

#### Adding a new test to CI
  Usually, fixing an existent feature or creating a new one requires editing/adding a new test for it in CI:  `src/tests/integration/test_foundry_prove.py`
  - If you are adding a new feature, you might want to add a new test for it in CI (see the tests for recently added features like [test_deployment_summary](https://github.com/runtimeverification/kontrol/blob/0c18ea7e846f9278624007c8072326d1ea1f95df/src/tests/integration/test_foundry_prove.py#L603) and [test_xml_report](https://github.com/runtimeverification/kontrol/blob/0c18ea7e846f9278624007c8072326d1ea1f95df/src/tests/integration/test_foundry_prove.py#L743)).
  - If you are addressing an issue that is reproducible with a Foundry test, then:
    - Add the test into `src/tests/integration/test-data/foundry/test`;
    - Edit the `foundry-{prove-all,skip,fail}` lists according to your fix. To make a test run on CI you should add a _signature_ of the test in these files. Tests in `foundry-fail` are expected to fail. For instance:
      - If the test was failing with `kontrol prove` and it is supposed to pass, then add the test to `foundry-prove-all` and make sure that the test is not in `foundry-prove-skip` (or `foundry-prove-skip-legacy` in case the test should also run in the legacy backend);
      - If the test was passing with `kontrol prove` and it is supposed to fail, then add the test to `foundry-fail` and make sure that the test is not in `foundry-prove-skip` (or `foundry-prove-skip-legacy` in case the test should also run in the legacy backend);
  - Run `make test-integration` locally to ensure all tests pass in CI.
  - Note: since `make test-integration` is time-expensive, before you can run your test to ensure it passes with: 
```
poetry run pytest src/tests/integration -k 'test_foundry_xml_report' --maxfail=1 --verbose --durations=0 --numprocesses=4 --dist=worksteal
```

#### Running kontrol with a custom `pyk` / `kevm`
- If your fix involves changes in `pyk` or `kevm`, you might want to run Kontrol with a custom `pyk`/`kevm`. If that is the case, follow these [instructions](https://github.com/runtimeverification/kontrol/issues/319).

#### Adding support for a new cheatcode
The `foundry_success` predicate, i.e., the criteria used to determine if a test is passing or failing, as well as the addresses needed to define cheatcodes, are in [foundry.md](https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/foundry.md).  The rules to support cheatcodes are located in [cheatcodes.md](https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/cheatcodes.md). At the top of the file there is the subconfiguration needed to implement the cheatcodes. The [structure of execution](https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/cheatcodes.md#structure-of-execution) presents how calls to the Foundry cheatcode address are handled. After understanding this infrastructure, implementing a new cheatcode resumes to:
##### 1. Add a new `call_foundry` rule for the cheatcode
```k
 rule [cheatcode.call.cheatcode]:
         <k> #cheatcode_call SELECTOR ARGS => logic implementation of the cheatcode ... </k>
      requires SELECTOR ==Int selector ( "cheatcode signature" )
```

##### 2. Add a rule for the selector
Example:
```k
rule ( selector ( "assume(bool)" )                             => 1281615202 )
```
If you are implementing a cheatcode that belongs to the list of selectors for non-implemented cheatcodes (end of the file), please move the rule for that selector into the list for the implemented cheatcodes.

##### 3. Editing the subconfiguration
If the cheatcode implementation requires additional information stored in the subconfiguration, please provide documentation on the new cell added. 

##### 4. Add tests for the cheatcode into the CI
- Check if the current [test-suite](https://github.com/runtimeverification/kontrol/tree/master/src/tests/integration/test-data/foundry/test) contains any tests for the cheatcode being implemented. If not, please add the tests you consider necessary;
- Make sure the tests are in `foundry-prove-all` list (or `foundry-fail` list if it is expected the tests to fail);
- Make sure the tests are removed from `foundry-prove-skip`;
- Check if the tests are in the `foundry-prove-skip-legacy`. If that is the case, remove them from that list. Run the tests locally with `kontrol prove --no-use-booster`. If a test takes more than 300s, it should be added again to `foundry-prove-skip-legacy`, otherwise it can be removed from that list;
- Run `make test` to ensure all the tests pass after your changes.
