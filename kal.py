import sys

from importlib import reload

import llvmlite

from termcolor import cprint

import kal_eval
import kal_repl

# ref.: https://github.com/frederickjeanguerin/pykaleidoscope


def run(**options):
    cprint(
        "Kaleidoscope REPL originally created by Frederic Guerin and distributed as free software\nReference: https://github.com/frederickjeanguerin/pykaleidoscope",
        color="magenta",
    )
    cprint(
        f"\nPython : {sys.version}\nLLVM   : {'.'.join((str(n) for n in llvmlite.binding.llvm_version_info))}\n",
        color="magenta",
    )
    while True:
        try:
            kal_repl.run(options)
            break
        except kal_repl.ReloadException:
            reload(kal_repl)
            continue


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run()
    else:
        try:
            with open("stdlib.kal", "r") as stdlib_file:
                kal_stdlib = stdlib_file.read()
            with open(sys.argv[1], "r") as kal_file:
                kal_repl.print_eval(
                    kal_eval.KaleidoscopeCodeEvaluator(),
                    kal_stdlib + kal_file.read(),
                    {"optimize": True, "llvmdump": True, "verbose": False},
                )
        except FileNotFoundError:
            kal_repl.errprint(f"File not found: '{sys.argv[1]}'")
