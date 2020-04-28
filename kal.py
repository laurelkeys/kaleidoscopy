import sys

from importlib import reload

import llvmlite

from termcolor import cprint

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
    run()
