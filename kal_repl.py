import sys
import copy

from importlib import reload

import colorama

from termcolor import cprint, colored

import kal_ir
import kal_ops
import kal_eval
import kal_lexer
import kal_parser

colorama.init()

# ref.: https://github.com/frederickjeanguerin/pykaleidoscope


class ReloadException(Exception):
    pass


history = []


USAGE = """
USAGE: Type Kaleidoscope code or enter one the following special commands:

    .exit or exit : Stop and exit the program.
    .functions    : List all available language functions and operators.
    .help or help : Show this message.
    .options      : Print the actual options settings.
    .reload or .. : Reload the python code and restart the REPL from scratch.
    .reset        : Reset the interpreting engine.
    .<file>       : Run the given .kal file.
    .<option>     : Toggle the given option on/off.
"""


def errprint(msg):
    cprint(msg, color="red", file=sys.stderr)


def print_eval(k, kal_code, options=None):
    """ Evaluate the given code with `k` using the given `options` and print the results. """
    results = k._evaluate(kal_code, options or {})
    try:
        for result in results:
            if (value := result.value) is not None:
                cprint(value, color="green")
            else:
                history.append(result.ast)

            if options.get("verbose"):
                print()
                cprint(result.unoptimized_ir, color="green")
                print()
                cprint(result.optimized_ir, color="magenta")
                print()

    except kal_parser.ParseError as err:
        errprint(f"ParseError: {str(err)}")

    except kal_ir.GenerateCodeError as err:
        errprint(f"GenerateCodeError: {str(err)}")
        # Reset the interpreter because kal_ir is now corrupted
        if not (reran_history := k.reset(history)):
            print(
                colored("Could not run history:", color="red"),
                ",".join((str(ast) for ast in history)),
            )

    except Exception as err:
        errprint(str(type(err)) + ": " + str(err))
        print(" Aborting... ")
        raise


def print_function_list(lst):
    for fn in lst:
        cprint(
            "{:>6} {:<20} ({})".format(
                "extern" if fn.is_declaration else "   def",
                fn.name,
                " ".join((arg.name for arg in fn.args)),
            ),
            color="yellow",
        )


def print_functions(k):
    # Operators
    print(colored("\nBuilt-in operators:", color="blue"), *kal_ops.operators.keys())

    # User-defined/extern functions
    user_functions, extern_functions = [], []
    for fn in sorted(k.code_generator.module.functions, key=lambda fn: fn.name):
        if fn.is_declaration:
            extern_functions.append(fn)
        else:
            user_functions.append(fn)

    cprint("\nUser-defined functions and operators:\n", color="blue")
    print_function_list(user_functions)

    cprint("\nExtern functions:\n", color="blue")
    print_function_list(extern_functions)


def run_repl_command(k, command, options):
    if command in options:
        options[command] = not options[command]  # toggle option
        print(command, "=", options[command])
    elif command in ["functions"]:
        print_functions(k)
    elif command in ["help", "?", ""]:
        print(USAGE)
    elif command in ["options"]:
        print(options)
    elif command in ["quit", "exit", "stop"]:
        sys.exit()
    elif command in ["reload", "."]:
        reload(kal_lexer)
        reload(kal_parser)
        reload(kal_ir)
        reload(kal_eval)
        raise ReloadException()
    elif command in ["reset"]:
        reload(kal_parser)
        k.reset()
        history = []
        run_repl_command(k, "stdlib.kal", {})
    elif command:
        # Here the command should be a filename
        try:
            with open(command) as kal_file:
                print_eval(k, kal_file.read(), options)
        except FileNotFoundError:
            errprint(f"File not found: '{command}'")


def run_command(k, command, options):
    print(colorama.Fore.YELLOW, end="")
    if not command:
        pass
    elif command in ["help", "quit", "exit", "stop"]:
        run_repl_command(k, command, options)
    elif command[0] == ".":
        run_repl_command(k, command[1:], options)
    else:
        # `command` is a Kaleidoscope code snippet, so run it
        print_eval(k, command, options)
    print(colorama.Style.RESET_ALL, end="")


def run(optimize=True, llvmdump=False, noexec=False, parseonly=False, verbose=False):
    options = locals()
    k = kal_eval.KaleidoscopeCodeEvaluator()

    # Enter a REPL loop
    cprint("Type help or a command to be interpreted", color="green")
    command = ".stdlib.kal"
    while not command in ["exit", "quit"]:
        try:
            run_command(k, command, options)
            print("K> ", end="")
            command = input().strip()
        except KeyboardInterrupt:
            sys.exit()


if __name__ == "__main__":
    import kal

    kal.run()
