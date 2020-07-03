import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import kal_ir
import kal_ast
import kal_eval
import kal_lexer
import kal_parser
import kal_bin_ops

del sys.path[0]
del sys
del os
