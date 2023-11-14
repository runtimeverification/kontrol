# Bug report archive triage manual

Bug report archives produces by [`pyk`](https://github.com/runtimeverification/pyk) contain the low-level steps that comprise an RPC server-powered proof (i.e. `kore-rpc`, `kore-rpc-booster`). In this document, we will be taking an in-depth look at the contents of a `bug_report.tag-gz` produced by `kontrol` and learning how to run individual requests and interpret the results.

## Setting up the environment

### Using `direnv`

It is useful to have save several path into dedicated environment variables when working on a bug report:

```
export BUG_REPORT_DIR=$(realpath .)
export KONTROL_KOMPILED_DIR=$(realpath ~/Workspace/RV/kontrol/pr/src/tests/integration/test-data/foundry/out/kompiled/)
export PYK_DIR=$(realpath ~/Workspace/RV/pyk/pr/)
```

### Producing a `bug_report.tar` for a proof

Usually real-world proofs fail somewhere deep in the KCFG. If there's a suspicion that the proof failure is due to the backend, it is necessary to make this failure reproducible by generating a bug report. To do that, one needs to attempt to advance the proof from the last "good" node, which would issue an RPC `"execute"` request to the server, which would fail and can then be scrutinized, and possible further minimized, in isolation.

As an example, let us consider one of the obviously failing tests in `kontrol/src/tests/integration/test-data/foundry-fail`:

```
$ cd kontrol/pr/src/tests/integration/test-data/foundry
$ kontrol build
...
$ kontrol prove --test AssertTest.test_assert_false --use-booster --reinit --verbose
...
PROOF FAILED: ('AssertTest.test_assert_false()', 0)
1 Failure nodes. (0 pending and 1 failing)

Failing nodes:

  Node id: 5
...
```

The proof assert false and fails at node 5. We intentionally will not look at the constraints output or the KCFG, and instead reattempt the proof and generate a bug report archive:

```
kontrol prove --test AssertTest.test_assert_false --use-booster --bug-report bug_report --no-simplify-init --verbose
```

Note that we intentionally don't supply the `--reinit`, so we do not re-run the proof from scratch, and instead just re-attempt the last request. The `--no-simplify-init` option ensures that we also skip the `"simplify"` requests for the initial and target nodes, as they are not useful at this stage.

### Running a single request with the RPC server

In this section, we will be looking at the necessary steps to run an `"execute"` request from a bug report archive. Other request types can be ran in the same way.

#### Preparing an `execute` request

The `"execute"` RPC requests are the main workhorse of a proof. They result in adding new nodes into KCFG by rewriting the configuration with the rules from the semantics to get new configurations. See [haskell-backend/docs/2022-07-18-JSON-RPC-Server-API.md#execute](https://github.com/runtimeverification/haskell-backend/blob/master/docs/2022-07-18-JSON-RPC-Server-API.md#execute) to learn more about the request and possible responses.

Let's extract the bug report archive into the its own directory and have a look inside:

```
$ tar -xf bug_report.tar --one-top-level
$ ls bug_report
commands  definition.kore  llvm_definition  rpc_139753641630768  rpc_139753685394832  server_instance.json  server_version.txt
```

We're particular interested in the `server_version.txt`, `server_instance.json`, and the rpc folders. In `server_version.txt` we find the Git revision of the server executable, and in `server_instance.json` the exact parameters the server was ran with:

```
$ cat server_instance.json
{"exe": "kore-rpc-booster", "module": "FOUNDRY-MAIN", "extra_args": ["--llvm-backend-library", "out/kompiled/llvm-library/interpreter.so", "--smt-timeout", "300", "--smt-retry-limit", "10"]}
```

The rpc folders containsthe raw JSON requests and their corresponding responses. There may be several rpc folders in a bug report, one for every `APRProof`. In this case we have two, because we have two subproofs: `AssertTest.setUp():0`, and the actual test function proof, `APRProof: AssertTest.test_assert_false():0`.

**NOTE**: it is not entirely clear to me at that point which rpc folder in the bug report we need! In this specific case, we need the one with the most requests... We can find the `"execute"` requetsts with something like
```
find . -iname *_request.json -exec sh -c "echo -n {}; jj -i {} method" \;
```
but this will not scale to large bug reports.

If working with a bug report manually (like in this tutorial), it is often convenient to rename the folder to `rpc_1` so it is less awkward to type the name. Let's have a look at the contents:

```
$ cp -r rpc_139753685394832 rpc_1
$ ls rpc_1
001_request.json  001_response.json  002_request.json  002_response.json
```

We see that there two request-response pairs. The files are named sequentially. i.e. the file `001_request.json` contains the first request and the file `001_response.json` contains its corresponding response. The last request is likely the reason of the proof failure.

Let us verify that this is indeed an `"execute"` request. It could be easily done with [`jq`](https://jqlang.github.io/jq/) or it's more robust analogue [`jj`](https://github.com/tidwall/jj):

```
$ cat rpc_1/002_request.json  | jj method
execute
```

The next thing that should be done is the removal of the `module` parameter, if it is unused. This allows to skip the `"add-module"` requests for unnecessary empty modules. If the proof takes advantage of proof reuse, than the modules will have to be added on every server restart. But let us assume we do not need dynamically loaded modules for now, and remove the parameter, copying the request into a fresh rpc directory:

```
$ mkdir rpc_2
$ cat rpc_1/003_request.json  | jj -D params.module -o rpc_2/003_request.json
```

We are now ready to submit the request to the server!

#### Starting the RPC-server

To start the RPC-server, one needs three inputs:
* the server executable, i.e. `kore-rpc-booster` or `kore-rpc`;
* the kompiled Kore definition, `definition.kore` --- it is always a part of the bug report. We need to use the one from the bug report, since we need the custom symbolic lemmas from this specific proof development;
* if running with Booster (i.e. the first component is `kore-rpc-booster`), the LLVM shared library, `interpreter.so`. While the bug report contains the necessary pieces to build the shared object, it also fine to reuse one build for Kontrol. One could build the library in the source checkout of KEVM/Kontrol and use the `KONTROL_KOMPILED_DIR` to keep track of it.

Note that the LLVM shared library file is called `interpreter.so` on Linux and `interpreter.dylib` on Mac.

Provided we have all these components in place, we can start the server in its own terminal window, as it's blocking:

```
kore-rpc-booster $BUG_REPORT_DIR/definition.kore --module FOUNDRY-MAIN --llvm-backend-library $KONTROL_KOMPILED_DIR/llvm-library/interpreter.so --server-port 12341 | tee $BUG_REPORT_DIR/kore-rpc-booster.log
```

The server will parse and internalize `definition.kore` and will ready to accept requests one it prints thew following:

```
[Info#proxy] Loading definition from definition.kore, main module "FOUNDRY-MAIN"
...
[Info#proxy] Starting RPC server
```

#### Submitting an `execute` request

While we have built a custom `rpc-client` executable that we use for integration tests in the `hs-backend-booster` repository, the request can as well be submitted using standard Unix tool such as `nc` or `curl`. Here we submit an `"execute"` request to the server listening on port `12341`:

```
cat $BUG_REPORT_DIR/rpc_2/003_request.json | nc -v 127.0.0.1 12341 | tee $BUG_REPORT_DIR/rpc_2/003_response_manual.json
```

### Using `pyk print --input kore-json` to pretty-print a response for manual analysis

```
cat $BUG_REPORT_DIR/rpc_2/003_response_manual.json | poetry -C $PYK_DIR run pyk print $KONTROL_KOMPILED_DIR /dev/stdin --input kore-json | tee $BUG_REPORT_DIR/rpc_2/003_response_manual.pretty
```

### Using `pyk rpc-kast` to convert a response into a new `"execute"` request

Convert `003_response.json` into an execute request, using `003_request.json` as reference for depth, module and log settings:

```
poetry -C ../../pyk/pr/ run pyk rpc-kast $KONTROL_KOMPILED_DIR 003_request.json 003_response.json --output-file 004_request.json
```


#### Modifying the request depth

```
$ mkdir rpc_2
$ cat rpc_2/028_request.json  | jj -v params.max-depth 1 -o rpc_2/028_request_depth_1.json
```

### Troubleshooting

**Problem** Server won't start. Fails with the message `Created bug report: hs-booster-proxy.tar`

**Solution**

Extract the `hs-booster-proxy.tar` and look at `error.log`. Most likely it will cannot find the LLVM library:

```
/tmp/hs-booster-proxy-7157284ace25249e/.log: withFile: user error (dlopen: /home/geo2a/Workspace/RV/evm-semantics/master/kevm-pyk/src/tests/integration/test-data/foundry/out/kompiled/llvm_library/interpreter.so: cannot open shared object file: No such file or directory
```

Make sure you have executed `kontol build` in you source checkout if Kontrol/KEVM Foundry proof suite. Also try `find . -iname interpreter.so` to locate the shared object.
