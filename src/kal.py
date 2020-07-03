import os
import sys
import argparse

from importlib import reload

import llvmlite

from termcolor import cprint

import kal_eval
import kal_repl

# ref.: https://github.com/frederickjeanguerin/pykaleidoscope


KAL_STDLIB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "stdlib.kal"))
KAL_STDLIB_EXTERN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "stdlibextern.kal"))


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
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, nargs="?")
    parser.add_argument("--stdlib", "-std", action="store_true")
    parser.add_argument("--stdlibextern", "-ext", action="store_true")
    args = parser.parse_args()

    if not args.file:
        run()

    else:
        kal_code = ""
        if args.stdlib:
            with open(KAL_STDLIB_PATH, "r") as stdlib_file:
                kal_code += stdlib_file.read()
        if args.stdlibextern:
            with open(KAL_STDLIB_EXTERN_PATH, "r") as stdlibextern_file:
                kal_code += stdlibextern_file.read()
        try:
            with open(args.file, "r") as kal_file:
                kal_code += kal_file.read()
                kal_repl.print_eval(
                    kal_eval.KaleidoscopeCodeEvaluator(),
                    kal_code,
                    {"optimize": True, "llvmdump": True, "verbose": False},
                )
        except FileNotFoundError:
            kal_repl.errprint(f"File not found: '{args.file}'")
