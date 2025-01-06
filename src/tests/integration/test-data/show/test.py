#! /usr/bin/env python3

# input: path to a kcfg file
# output: cse steps

import re
import sys

if __name__ == "__main__":
    kcfg_path = sys.argv[1]

    with open(kcfg_path, "r") as f:
        prev_node_id = None
        curr_node_id = None
        is_calling = False
        is_callee = False
        counter = 0
        for line in f:
            # after the ┌─, ├─, └─ is the node id
            for match in re.finditer(r"[┌└├]─ (\d+)", line):
                prev_node_id = curr_node_id
                curr_node_id = match.group(1)
                if is_callee:
                    print(f'{prev_node_id} -> {curr_node_id}')
                    is_callee = False
                    counter += 1
            # if the line has "k: #execute ~> #return", then it tries to call a function
            if "k: #execute ~> #return" in line:
                is_calling = True
            # if is_calling and the line has "(\d+ step)"
            if is_calling and re.search(r"\d+ step", line):
                is_calling = False
                steps = int(re.search(r"(\d+) step", line).group(1))
                if steps == 1:
                    is_callee = True
    print(f"Total CSE Steps: {counter}")
