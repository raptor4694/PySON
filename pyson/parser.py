import math
import ast
import re
from keyword import iskeyword
from inspect import isgenerator, ismethod
from typing import *
from collections import (
    namedtuple,
    deque,
    Counter,
    OrderedDict,
    ChainMap
)
from .tokenize import *
from .util import *

class DataParseError(SyntaxError):
    def __init__(self, message, *args, **kwargs):
        if message is not None and not isinstance(message, str):
            raise TypeError(f"DataParseError() argument 1 must be a string, not {type(message).__name__!r}")

        if len(args) == 0:
            if len(kwargs) == 0:
                super().__init__(message)

            elif len(kwargs) == 1 and 'at' in kwargs:
                at = kwargs['at']
                if not isinstance(at, tuple) or len(at) != 4 or not isinstance(at[0], str) or not isinstance(at[1], int) or not isinstance(at[2], int) or not isinstance(at[3], str):
                    raise TypeError(f"DataParseError() 'at' keyword argument must be a (filename, line#, column#, line) tuple, not {at if isinstance(at, tuple) else type(at).__name__!r}")
                super().__init__(message, at)

            elif 'token' in kwargs and (len(kwargs) == 1 or len(kwargs) == 2 and 'filename' in kwargs):
                token = kwargs['token']
                if not isinstance(token, TokenInfo):
                    raise TypeError(f"DataParseError() 'token' keyword argument must be TokenInfo, not {type(token).__name__!r}")

                if 'filename' in kwargs:
                    filename = kwargs['filename']
                    if not isinstance(filename, str):
                        raise TypeError(f"DataParseError() 'filename' keyword argument must be a string, not {type(filename).__name__!r}")
                else:
                    filename = '<unknown source>'

                super().__init__(message, (filename, *token.start, token.line))

            else:
                if len(kwargs) == 2 and 'at' in kwargs and 'got' not in kwargs or len(kwargs) == 3:
                    args = set()
                    if 'at' in kwargs:
                        args.add('at')
                    if 'token' in kwargs:
                        args.add('token')
                    if 'filename' in kwargs:
                        args.add('filename')
                    raise ValueError("DataParseError() keyword arguments {0} are mutually exclusive".format(', '.join(repr(arg) for arg in args)))
                else:
                    raise ValueError("DataParseError() illegal keyword arguments " + ', '.join(repr(name) for name in set(kwargs.keys()) - {'token', 'filename', 'at'}))

        elif len(args) == 1:
            if len(kwargs) == 0:
                arg = args[0]
                if isinstance(arg, TokenInfo):
                    super().__init__(message, ('<unknown source>', *arg.start, arg.line))

                elif isinstance(arg, tuple):
                    if len(arg) != 4 or not isinstance(arg[0], str) or not isinstance(arg[1], int) or not isinstance(arg[2], int) or not isinstance(arg[3], str):
                        raise TypeError(f"DataParseError() argument 2 must be a (filename, line#, column#, line) tuple, not {type(arg).__name__!r}")

                    super().__init__(message, arg)

                else:
                    raise TypeError(f"DataParseError() argument 2 must be TokenInfo or a (filename, line#, column#, line) tuple, not {type(arg).__name__!r}")

            elif len(kwargs) == 1 and 'filename' in kwargs:
                if not isinstance(arg, TokenInfo):
                    raise TypeError(f"DataParseError() argument 2 must be TokenInfo, not {type(arg).__name__!r}")

                filename = kwargs['filename']
                if not isinstance(filename, str):
                    raise TypeError(f"DataParseError() 'filename' keyword argument must be a string, not {type(filename).__name__!r}")

                super().__init__(message, (filename, *arg.start, arg.line))

            elif len(kwargs) == 1 and 'token' in kwargs:
                if not isinstance(arg, str):
                    raise TypeError(f"DataParseError() argument 2 must be a string, not {type(arg).__name__!r}")
                
                token = kwargs['token']
                if not isinstance(token, TokenInfo):
                    raise TypeError(f"DataParseError() 'token' keyword argument must be TokenInfo, not {type(token).__name__!r}")

                super().__init__(message, (arg, *token.start, token.line))

            else:
                has_at = 'at' in kwargs or isinstance(arg, str) and 'token' not in kwargs
                has_token = 'token' in kwargs or isinstance(arg, TokenInfo)
                has_filename = 'filename' in kwargs or isinstance(arg, str) and has_token
                if len(kwargs) in (1,2,3) and (has_at or has_token or has_filename):
                    args = set()
                    if has_at:
                        args.add('at')
                    if has_token:
                        args.add('token')
                    if has_filename:
                        args.add('filename')
                    raise ValueError("DataParseError() keyword arguments {0} are mutually exclusive".format(', '.join(repr(arg) for arg in args)))

                else:
                    raise ValueError("DataParseError() illegal keyword arguments " + ', '.join(repr(name) for name in set(kwargs.keys()) - {'token', 'filename', 'at'}))

        elif len(args) == 2:
            if len(kwargs) != 0:
                raise ValueError("DataParseError() illegal keyword arguments " + ', '.join(repr(name) for name in kwargs))
            
            arg1 = args[0]
            arg2 = args[1]

            if isinstance(arg1, str):
                if not isinstance(arg2, TokenInfo):
                    raise TypeError(f"DataParseError() argument 3 must be TokenInfo, not {type(arg2).__name__!r}")
                filename = arg1
                token = arg2

            elif isinstance(arg1, TokenInfo):
                if not isinstance(arg2, str):
                    raise TypeError(f"DataParseError() argument 3 must be string, not {type(arg2).__name__!r}")
                filename = arg2
                token = arg1

            else:
                raise TypeError(f"DataParseError() argument 2 must be TokenInfo or string, not {type(arg1).__name__!r}")

            super().__init__(message, (filename, *token.start, token.line))

        else:
            raise ValueError("DataParseError() too many arguments")
        

def loadx(tokens, filename='<unknown source>', allow_Infinity_and_NaN=True):
    """ Loads PySON from a number of different data types:

    ``tokens`` can be a str, bytes, or bytearray object, 
    in which case ``loads`` is called.

    ``tokens`` can be a callable object,
    in which case it is assumed to be a ``readline`` method as
    described by the ``tokenize`` module.

    ``tokens`` can be a subclass of ``io.IOBase`` (a file pointer),
    in which case `tokenize` is called on the object's ``readline`` method.

    ``tokens`` can be an iterable of ``TokenInfo`` objects,
    in which case the object gets filtered to remove any ENCODING or COMMENT tokens.
    """
    if isinstance(tokens, (str, bytes, bytearray)):
        return loads(tokens, 'utf-8', allow_Infinity_and_NaN)
    else:
        if filename == '<unknown source>' and hasattr(tokens, 'name'):
            filename = tokens.name
        if callable(tokens):
            tokens = tokenize(tokens, yield_encoding=False, yield_comments=False)
        else:
            import io
            if isinstance(tokens, io.IOBase):
                tokens = tokenize(tokens.readline, yield_encoding=False, yield_comments=False)
            else:
                from inspect import isgenerator
                if not isgenerator(tokens):
                    try:
                        tokens = iter(tokens)
                    except TypeError as e:
                        raise TypeError(f"Don't know how to parse {type(tokens).__name__!r} instances") from e
                tokens = filter(lambda token: token.type not in (ENCODING, COMMENT), tokens)

        return loadt(tokens, filename, allow_Infinity_and_NaN)

def load(fp, allow_Infinity_and_NaN=True):
    """ Load PySON from a file pointer or file name

    This method expects the file to have been opened in 'rb' (read-binary) mode, if the argument is a file pointer.
    """
    if isinstance(fp, str):
        with open(fp, 'rb') as fp:
            tokens = tokenize(fp.readline, yield_encoding=False, yield_comments=False)
    else:
        tokens = tokenize(fp.readline, yield_encoding=False, yield_comments=False)

    return loadt(tokens, fp.name, allow_Infinity_and_NaN)

def loads(string, encoding='utf-8', allow_Infinity_and_NaN=True):
    """ Load PySON from a string or a bytes-like object """
    lines = iter(string.splitlines(keepends=True))
    if isinstance(string, str):
        def readline():
            return bytes(next(lines), encoding)
    elif isinstance(string, (bytes, bytearray)):
        def readline():
            return next(lines)
    else:
        raise TypeError("loads() argument needs to be either a string or bytes object")

    tokens = tokenize(readline, yield_encoding=False, yield_comments=False)

    return loadt(tokens, '<string>', allow_Infinity_and_NaN)

def loadt(tokens, filename='<unknown source>', allow_Infinity_and_NaN=True):
    """ Load PySON from an iterable of TokenInfos (as returned by pycson.tokenize(yield_encoding=False, yield_comments=False)) """
    return DataParser(tokens, filename, allow_Infinity_and_NaN).parse_all()
    # token: TokenInfo = None
    # last: TokenInfo = None
    
    # def expect(test):
    #     result = accept(test)
    #     if result:
    #         return result
    #     else:
    #         def make_test_str(test):
    #             if isinstance(test, str):
    #                 return repr(test)
    #             elif isinstance(test, int):
    #                 return tok_name[test]
    #             else:
    #                 def expand(t):
    #                     for elem in t:
    #                         if isinstance(elem, tuple):
    #                             yield from expand(elem)
    #                         else:
    #                             yield make_test_str(elem)
    #                 return ' or '.join(expand(test))
    #         raise DataParseError(f'expected {make_test_str(test)}, found {tok_name[token.exact_type]} {token.string!r}', filename, token)

    # def accept(test):
    #     result = token.string or True
    #     if has_next(test):
    #         proceed()
    #         return result

    # def has_next(test):
    #     return tok_match(token, test)

    # def tok_match(token, test):
    #     if isinstance(test, tuple):
    #         for elem in test:
    #             if tok_match(token, elem):
    #                 return True
    #         else:
    #             return False
    #     elif isinstance(test, str):
    #         return token.string == test
    #     elif isinstance(test, int):
    #         return token.exact_type == test
    #     else:
    #         raise ValueError(f'must be string or int or a tuple thereof, not {type(test).__name__}')

    # def proceed():
    #     nonlocal token, last
    #     try:
    #         last = token
    #         token = next(tokens)
    #         if last is not None:
    #             return last.string
    #     except StopIteration as e:
    #         raise DataParseError(f'unexpected end of token stream', at=(filename, *token.end, token.line)) from e

    # def skip_blanks():
    #     nonlocal last
    #     temp = last
    #     while token.type in (NEWLINE, INDENT, DEDENT, NL):
    #         proceed()
    #     last = temp

    # # -------------------------------------

    # #region constants
    # if python_constants:
    #     INFINITY = 'inf'
    #     NAN = 'nan'
    #     TRUE = 'True'
    #     FALSE = 'False'
    #     NONE = 'None'
    # else:
    #     INFINITY = 'Infinity'
    #     NAN = 'NaN'
    #     TRUE = 'true'
    #     FALSE = 'false'
    #     NONE = 'null'
    # P_INFINITY = '+' + INFINITY
    # N_INFINITY = '-' + INFINITY
    # INFINITY_J = INFINITY + 'J'
    # INFINITY_j = INFINITY + 'j'
    # P_INFINITY_J = P_INFINITY + 'J'
    # P_INFINITY_j = P_INFINITY + 'j'
    # N_INFINITY_J = N_INFINITY + 'J'
    # N_INFINITY_j = N_INFINITY + 'j'
    # P_NAN = '+' + NAN
    # N_NAN = '-' + NAN
    # NAN_J = NAN + 'J'
    # NAN_j = NAN + 'j'
    # P_NAN_J = P_NAN + 'J'
    # P_NAN_j = P_NAN + 'j'
    # N_NAN_J = N_NAN + 'J'
    # N_NAN_j = N_NAN + 'j'

    # P_INFINITY_Jj = (P_INFINITY_J, P_INFINITY_j)
    # N_INFINITY_Jj = (N_INFINITY_J, N_INFINITY_j)
    # P_NAN_Jj = (P_NAN_J, P_NAN_j)
    # N_NAN_Jj = (N_NAN_J, N_NAN_j)

    # NUM_CONSTANTS = (INFINITY, P_INFINITY, N_INFINITY, NAN, P_NAN, N_NAN, INFINITY_J, INFINITY_j, P_INFINITY_J, P_INFINITY_j, N_INFINITY_J, N_INFINITY_j, NAN_J, NAN_j, P_NAN_J, P_NAN_j, N_NAN_J, N_NAN_j)
    # OTHER_CONSTANTS = (TRUE, FALSE, NONE)
    # #endregion

    # def parse_key():
    #     if token.type == STRING:
    #         result = ast.literal_eval(proceed())
    #     else:
    #         last = token
    #         result = expect((NAME, STRING, NUMBER))
    #         if allow_Infinity_and_NaN and result in NUM_CONSTANTS or result in OTHER_CONSTANTS:
    #             raise DataParseError(f"invalid key {result!r}", last, filename)
    #     return result

    # def parse_value():
    #     if token.string == '[':
    #         return parse_list()
    #     elif token.string == '{':
    #         obj = parse_inline_object()
    #         expect(NEWLINE)
    #         return obj
    #     elif token.type == NEWLINE:
    #         return parse_object(allow_list=True)
    #     else:
    #         return parse_simple_value()

    # def parse_inline_value():
    #     if token.string == '[':
    #         return parse_inline_list()
    #     elif token.string == '{':
    #         return parse_inline_object()
    #     else:
    #         return parse_simple_inline_value()

    # def parse_simple_value():
    #     value = parse_simple_inline_value()
    #     expect(NEWLINE)
    #     return value  

    # def parse_number_suffix(result):
    #     if isinstance(result, (int, float)):
    #         if token.type == NUMBER:
    #             if token.string[-1] not in 'jJ':
    #                 raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #             result += ast.literal_eval(proceed())
    #         elif allow_Infinity_and_NaN:
    #             if accept(P_INFINITY_Jj):
    #                 result = complex(result, math.inf)
    #             elif accept(N_INFINITY_Jj):
    #                 result = complex(result, -math.inf)
    #             elif accept((P_NAN_Jj, N_NAN_Jj)):
    #                 result = complex(result, math.nan)
    #     return result

    # def parse_simple_inline_value():
    #     return parse_simple_inline_value_0(token, proceed, accept)

    # def parse_simple_inline_value_0(token, proceed, accept):
    #     if token.type == NUMBER:
    #         result = ast.literal_eval(proceed())
    #         if not isinstance(result, complex):
    #             result = parse_number_suffix(result)
    #         return result
    #     # elif token.exact_type == PLUS:
    #     #     proceed()
    #     #     if accept(INFINITY):
    #     #         return math.inf if allow_Infinity_and_NaN else INFINITY
    #     #     elif accept(NAN):
    #     #         return math.nan if allow_Infinity_and_NaN else NAN
    #     #     if token.type != NUMBER:
    #     #         raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #     #     return parse_simple_inline_value()
    #     # elif token.exact_type == MINUS:
    #     #     proceed()
    #     #     if accept(INFINITY):
    #     #         return -math.inf if allow_Infinity_and_NaN else N_INFINITY
    #     #     elif accept(NAN):
    #     #         return -math.nan if allow_Infinity_and_NaN else N_NAN
    #     #     if token.type != NUMBER:
    #     #         raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #     #     result = -ast.literal_eval(proceed())
    #     #     if not isinstance(result, complex) and token.string in ('+', '-'):
    #     #         neg = token.string == '-'
    #     #         proceed()
    #     #         if token.type != NUMBER or token.string[-1] not in 'jJ':
    #     #             raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #     #         x = ast.literal_eval(proceed())
    #     #         if neg:
    #     #             result -= x
    #     #         else:
    #     #             result += x
    #     #     return result
    #     elif token.type == STRING:
    #         return ast.literal_eval(proceed())
    #     elif accept(TRUE):
    #         return True
    #     elif accept(FALSE):
    #         return False
    #     elif accept(NONE):
    #         return None
    #     elif allow_Infinity_and_NaN and accept((INFINITY, P_INFINITY)):
    #         return parse_number_suffix(math.inf)
    #     elif allow_Infinity_and_NaN and accept(N_INFINITY):
    #         return parse_number_suffix(-math.inf)
    #     elif allow_Infinity_and_NaN and accept((NAN, P_NAN)):
    #         return parse_number_suffix(math.nan)
    #     elif allow_Infinity_and_NaN and token.string == N_NAN:
    #         proceed()
    #         return parse_number_suffix(-math.nan)
    #     elif allow_Infinity_and_NaN and accept((INFINITY_J, INFINITY_j, P_INFINITY_Jj)):
    #         return complex(0, math.inf)
    #     elif allow_Infinity_and_NaN and accept(N_INFINITY_Jj):
    #         return complex(0, -math.inf)
    #     elif allow_Infinity_and_NaN and accept((NAN_J, NAN_j, P_NAN_Jj)):
    #         return complex(0, math.nan)
    #     elif allow_Infinity_and_NaN and accept(N_NAN_Jj):
    #         return complex(0, -math.nan)
    #     elif token.type == NAME:
    #         return proceed()
    #     else:
    #         raise DataParseError(f"syntax error at token {tok_name[token.exact_type]} {token.string!r}", token, filename)

    # def parse_key_value():
    #     key = parse_key()
    #     expect(':')
    #     value = parse_key_value_rest()
    #     return key, value

    # def parse_key_value_rest():
    #     if token.type in (NAME, STRING, NUMBER):
    #         last_token = token
    #         proceed()
    #         if accept(':'):
    #             if last_token.type == STRING:
    #                 key = ast.literal_eval(last_token.string)
    #             else:
    #                 key = last_token.string
    #             return { (key): parse_key_value_rest() }
    #         else:
    #             called = False
    #             def _proceed():
    #                 nonlocal called
    #                 if called:
    #                     return proceed()
    #                 else:
    #                     called = True
    #                     return last_token.string
    #             def _accept(test):
    #                 nonlocal called
    #                 if called:
    #                     return accept(test)
    #                 elif tok_match(last_token, test):
    #                     called = True
    #                     return last_token.string
    #             return parse_simple_inline_value_0(last_token, _proceed, _accept)
    #     else:
    #         return parse_value()

    # def parse_inline_key_value():
    #     key = parse_key()
    #     skip_blanks()
    #     expect(':')
    #     skip_blanks()
    #     last_token = token
    #     value = parse_inline_value()
    #     skip_blanks()
    #     if last_token.type in (NAME, STRING, NUMBER) and accept(':'):
    #         skip_blanks()
    #         if last_token.type == STRING:
    #             key = ast.literal_eval(last_token.string)
    #         else:
    #             key = last_token.string
    #         value = { (key): parse_inline_value() }
        
    #     return key, value

    # def parse_object(allow_list=False, allow_brackets=True):
    #     expect(NEWLINE)
    #     if allow_brackets and token.string == '{':
    #         obj = parse_inline_object()
    #         expect(NEWLINE)
    #         return obj
    #     elif allow_list and token.string == '[':
    #         return parse_list()
    #     expect(INDENT)
    #     if allow_brackets and token.string == '{':
    #         obj = parse_inline_object()
    #         expect(NEWLINE)
    #         expect(DEDENT)
    #         return obj
    #     elif allow_list and token.string == '[':
    #         lst = parse_list()
    #         expect(DEDENT)
    #         return lst
    #     obj = {}
    #     while token.type != DEDENT:
    #         start_token = token
    #         key, value = parse_key_value()
    #         if key in obj:
    #             raise DataParseError(f"duplicate key {key!r}", start_token, filename)
    #         obj[key] = value
    #     expect(DEDENT)
    #     return obj

    # def parse_inline_object():
    #     expect('{')
    #     if token.type == NEWLINE:
    #         obj = parse_object(allow_brackets=False)
    #     else:
    #         skip_blanks()
    #         obj = {}
    #         if token.string != '}':
    #             key, value = parse_inline_key_value()
    #             obj[key] = value
    #             skip_blanks()
    #             if accept(','):
    #                 skip_blanks()
    #                 if token.string != '}':
    #                     start_token = token
    #                     key, value = parse_inline_key_value()
    #                     if key in obj:
    #                         raise DataParseError(f"duplicate key {key!r}", start_token, filename)
    #                     obj[key] = value
    #                     skip_blanks()
    #                     while accept(','):
    #                         skip_blanks()
    #                         if token.string == '}':
    #                             break
    #                         start_token = token
    #                         key, value = parse_inline_key_value()
    #                         if key in obj:
    #                             raise DataParseError(f"duplicate key {key!r}", start_token, filename)
    #                         obj[key] = value
    #                         skip_blanks()

    #             elif token.string != '}':
    #                 start_token = token
    #                 key, value = parse_inline_key_value()
    #                 if key in obj:
    #                     raise DataParseError(f"duplicate key {key!r}", start_token, filename)
    #                 obj[key] = value
    #                 skip_blanks()
    #                 while token.string != '}':
    #                     start_token = token
    #                     key, value = parse_inline_key_value()
    #                     if key in obj:
    #                         raise DataParseError(f"duplicate key {key!r}", start_token, filename)
    #                     obj[key] = value
    #                     skip_blanks()

    #     expect('}')
    #     return obj

    # def parse_list():
    #     lst = parse_inline_list()
    #     expect(NEWLINE)
    #     return lst
    #     # expect('[')
    #     # lst = []
    #     # if accept(NL):
    #     #     skip_blanks()
    #     #     if token.string != ']':
    #     #         lst.append(parse_inline_value())
    #     #         if accept(','):
    #     #             skip_blanks()                               # ⎫
    #     #             if token.string != ']':                     # ⎪
    #     #                 lst.append(parse_inline_value())        # ⎪
    #     #                 skip_blanks()                           # ⎪
    #     #                 while accept(','):                      # ⎩ ___ 1
    #     #                     skip_blanks()                       # ⎧
    #     #                     if token.string == ']':             # ⎪
    #     #                         break                           # ⎪
    #     #                     lst.append(parse_inline_value())    # ⎪ 
    #     #                     skip_blanks()                       # ⎭

    #     #         elif accept(NL):
    #     #             skip_blanks()
    #     #             if accept(','):
    #     #                 skip_blanks()                               # ⎫
    #     #                 if token.string != ']':                     # ⎪
    #     #                     lst.append(parse_inline_value())        # ⎪
    #     #                     skip_blanks()                           # ⎪
    #     #                     while accept(','):                      # ⎩ ___ 1
    #     #                         skip_blanks()                       # ⎧
    #     #                         if token.string == ']':             # ⎪
    #     #                             break                           # ⎪
    #     #                         lst.append(parse_inline_value())    # ⎪ 
    #     #                         skip_blanks()                       # ⎭

    #     #             elif token.string != ']':
    #     #                 lst.append(parse_inline_value())
    #     #                 while accept(NL):
    #     #                     skip_blanks()
    #     #                     if token.string == ']':
    #     #                         break
    #     #                     lst.append(parse_inline_value())

    #     #         elif token.string != ']':
    #     #             expect((NL, ',')) # raises error
                    
    #     # else:
    #     #     skip_blanks()
    #     #     if token.string != ']':
    #     #         lst.append(parse_inline_value())
    #     #         skip_blanks()
    #     #         while accept(','):
    #     #             skip_blanks()
    #     #             if token.string == ']':
    #     #                 break
    #     #             lst.append(parse_inline_value())
    #     #             skip_blanks()

    #     # expect(']')
    #     # expect(NEWLINE)
    #     # return lst

    # def parse_inline_list():
    #     expect('[')
    #     lst = []
    #     skip_blanks()
    #     if token.string != ']':
    #         last_token = token
    #         lst.append(parse_inline_value())
    #         skip_blanks()
    #         if last_token.type in (NAME, STRING, NUMBER) and accept(':'):
    #             skip_blanks()
    #             obj = {}
    #             lst.append(obj)
    #             if last_token.type == STRING:
    #                 key = ast.literal_eval(last_token.string)
    #             else:
    #                 key = last_token.string
    #             obj[key] = parse_inline_value()
    #             skip_blanks()
    #             while token.string != ']' and token.type != ENDMARKER:
    #                 key, value = parse_inline_key_value()
    #                 skip_blanks()
    #                 if key in obj:
    #                     obj = {}
    #                     lst.append(obj)
    #                 obj[key] = value

    #         else:       
    #             skip_blanks()
    #             if accept(','):
    #                 skip_blanks()
    #                 if token.string != ']':
    #                     lst.append(parse_inline_value())
    #                     skip_blanks()
    #                     while accept(','):
    #                         skip_blanks()
    #                         if token.string == ']':
    #                             break
    #                         lst.append(parse_inline_value())
    #                         skip_blanks()
                
    #             elif token.string != ']':
    #                 lst.append(parse_inline_value())
    #                 skip_blanks()
    #                 while token.string != ']' and token.type != ENDMARKER:
    #                     lst.append(parse_inline_value())
    #                     skip_blanks()

    #     expect(']')
    #     return lst

    # # -------------------------------------

    # proceed()

    # if token.string == '{':
    #     obj = parse_inline_object()
    #     accept(NEWLINE)

    # elif token.type != ENDMARKER:
    #     obj = {}
    #     key, value = parse_key_value()
    #     obj[key] = value

    #     while token.type != ENDMARKER:
    #         start_token = token
    #         key, value = parse_key_value()
    #         if key in obj:
    #             raise DataParseError(f"duplicate key {key!r}", start_token, filename)
    #         obj[key] = value

    #     if token.type != ENDMARKER:
    #         if token.type == INDENT:
    #             raise DataParseError("unexpected indent", filename, token)
    #         elif token.type == DEDENT:
    #             raise DataParseError("unexpected dedent", filename, token)
    #         else:
    #             raise DataParseError(f"unexpected token {tok_name[token.exact_type]!r}", filename, token)

    # else:
    #     obj = {}

    # return obj

Value = Union[set, list, tuple, dict, str, int, float, complex, None]
TokenTest = Union[str, int, Iterable[Union[str, int]]]

class DataParser:
    key_types = (NAME, STRING, NUMBER)
    num_list_start = re.compile(r"(?:0+(?:_+0+)*_*1|1)\.")

    def num_list_regex(self, num):
        def test(token):
            return token.type == NUMBER and token.string.endswith('.') and int(token.string[:-1]) == num
        return test

    def __init__(self, tokens: Iterable[TokenInfo], filename='<unknown source>', allow_Infinity_and_NaN=True, python_constants=True, allow_imports=True):
        if not isinstance(filename, str):
            raise TypeError(f"'filename' must be a string, not {type(filename).__name__!r}")
        self.tokens = LookAheadListIterator(tokens)
        if len(self.tokens) == 0:
            raise ValueError("invalid token list: no tokens given")
        if self.tokens[-1].type != ENDMARKER:
            raise ValueError("invalid token list: did not end with an ENDMARKER token")
        self.tokens.default = self.tokens[-1]
        self.filename = filename
        self.allow_inf_nan = allow_Infinity_and_NaN
        self.allow_imports = allow_imports
        self.import_globals = {
            'set': set,
            'tuple': tuple,
            'dict': dict,
            'str': str,
            'int': int,
            'float': float,
            'complex': complex,
            'frozenset': frozenset,
            'bytearray': bytearray,
            'bytes': bytes,
            'chr': chr,
            'ord': ord,
            'sorted': sorted,
            'range': range,
            'reversed': reversed,
            'namedtuple': namedtuple,
            'deque': deque,
            'Counter': Counter,
            'OrderedDict': OrderedDict
        }
        if allow_imports:
            self.import_locals = {}
        self.references = ChainMap()
        self.names = []
        if python_constants:
            self.inf = 'inf'
            self.nan = 'nan'
            self.true = 'True'
            self.false = 'False'
            self.none = 'None'
        else:
            self.inf = 'Infinity'
            self.nan = 'NaN'
            self.true = 'true'
            self.false = 'false'
            self.none = 'null'
        self.ninf = '-' + self.inf
        self.nnan = '-' + self.nan
        pinf = '+' + self.inf
        pnan = '+' + self.nan
        self.inf = (self.inf, pinf)
        self.nan = (self.nan, pnan)
        self.infj = (*(x+'j' for x in self.inf), *(x+'J' for x in self.inf))
        self.pinfj = (pinf + 'j', pinf + 'J')
        self.nanj = (*(x+'j' for x in self.nan), *(x+'J' for x in self.nan))
        self.pnanj = (pnan + 'j', pnan + 'J')
        self.ninfj = (self.ninf + 'j', self.ninf + 'J')
        self.nnanj = (self.nnan + 'j', self.nnan + 'J')
        if self.token.type == ENCODING:
            next(self.tokens)
        # Skip leading comments
        while self.token.type == COMMENT:
            last = self.token
            next(self.tokens)
            if self.token.type == NEWLINE:
                idx = last.line.index(last.string)
                sub = last.line[0:idx]
                if sub == "" or sub.isspace():
                    next(self.tokens)

        class ScopeManager:
            def __init__(self, parser):
                self.parser = parser
            def __enter__(self): pass
            def __exit__(self, exc_typ, exc_val, exc_tb):
                del self.parser.references.maps[0]
                if not (exc_typ or exc_val or exc_tb) and hasattr(self.parser, 'value'):
                    self.parser.references.maps[-1][self.parser.current_name] = self.parser.value
                    if len(self.parser.names) > 1:
                        self.parser.references[self.parser.names[-1]] = self.parser.value
                    del self.parser.value
                del self.parser.names[-1]

        self._scope = ScopeManager(self)

    @property
    def current_name(self) -> str:
        return '.'.join(self.names)
        
    @property
    def token(self) -> TokenInfo:
        return self.tokens.current

    @property
    def last(self) -> TokenInfo:
        return self.tokens.last

    def next(self) -> str:
        result = self.token.string
        next(self.tokens)
        while self.token.type == COMMENT:
            last = self.token
            next(self.tokens)
            if self.token.type == NEWLINE:
                idx = last.line.index(last.string)
                sub = last.line[0:idx]
                if sub == "" or sub.isspace():
                    next(self.tokens)
        return result

    def _test_str(self, test: TokenTest) -> str:
        if isinstance(test, int):
            return tok_name[test]
        elif isinstance(test, (str, re.Pattern)):
            return repr(test)
        else:
            return join_natural((self._test_str(x) for x in test), word='or')

    def _tok_str(self, token: TokenInfo) -> str:
        if token.type in (NL, INDENT, DEDENT, ENDMARKER, ENCODING):
            return tok_name[token.type]
        elif token.type == STRING:
            return token.string
        else:
            return repr(token.string)

    def tok_match(self, token: TokenInfo, test: TokenTest) -> bool:
        if isinstance(test, str):
            return token.string == test
        elif isinstance(test, int):
            return token.exact_type == test
        elif isinstance(test, re.Pattern):
            return bool(test.match(token.string))
        elif callable(test):
            return bool(test(token))
        else:
            for subtest in test:
                if self.tok_match(token, subtest):
                    return True
            return False

    def eat(self, *tests: Tuple[TokenTest, ...], looped=False) -> Union[str, None]:
        self.tokens.push_marker()
        last = None
        for test in tests:
            if looped and self.token.type == ENDMARKER:
                self.tokens.pop_marker(reset=False)
                return True
            if not self.tok_match(self.token, test):
                self.tokens.pop_marker(reset=True)
                return None
            last = self.token.string or True
            self.next()
        self.tokens.pop_marker(reset=False)
        return last

    def test(self, *tests: Tuple[TokenTest, ...], looped=False) -> bool:
        self.tokens.push_marker()
        for test in tests:
            if looped and self.token.type == ENDMARKER:
                self.tokens.pop_marker(reset=False)
                return True
            if not self.tok_match(self.token, test):
                self.tokens.pop_marker(reset=True)
                return False
            self.next()
        self.tokens.pop_marker(reset=True)
        return True

    def expect(self, *tests: Tuple[TokenTest, ...]) -> Union[str, None]:
        result = self.eat(*tests)
        if not result:
            raise self.expected(*tests)
        return result

    def expected(self, *tests: Tuple[TokenTest, ...]) -> DataParseError:
        raise DataParseError(f'expected {" ".join(self._test_str(x) for x in tests)}, got {" ".join(self._tok_str(token) for token in self.tokens[self.tokens.marker:self.tokens.marker+len(tests)])}', at=self.position())

    def skip_blanks(self):
        while self.token.type == NL or self.token.type == NEWLINE and not self.tokens.look(1).type in (INDENT, DEDENT): # in (NEWLINE, INDENT, DEDENT, NL):
            self.next()
        
    def position(self) -> Tuple[str, int, int, str]:
        """ Returns a tuple of (filename, line#, column#, line) """
        return (self.filename, *self.token.start, self.token.line)

    def eat_newline(self) -> bool:
        if self.last.type != DEDENT:
            return self.eat(NEWLINE)
        else:
            return True

    def get_imported_type(self, name: str, start: TokenInfo):
        try:
            return self.import_globals[name]
        except KeyError:
            raise DataParseError(f"no type {name!r} has been imported", self.filename, start)

    def copy(self, value):
        if isinstance(value, dict):
            newvalue = type(value)()
            for key, value in value.items():
                newvalue[key] = self.copy(value)
            return newvalue
        if isinstance(value, set):
            newvalue = type(value)()
            for elem in value:
                newvalue.add(self.copy(elem))
            return newvalue
        if isinstance(value, list):
            newvalue = type(value)()
            for elem in value:
                newvalue.append(self.copy(elem))
            return newvalue
        if isinstance(value, tuple):
            return type(value)([self.copy(elem) for elem in value])
        if hasattr(value, 'copy'):
            copy = getattr(value, 'copy')
            if ismethod(copy):
                return copy()
        return value

    def enter(self, name):
        # if self.names:
        #     self.names.append(f"{self.names[-1]}.{name}")
        # else:
        #     self.names.append(str(name))
        self.names.append(str(name))
        self.references.maps.insert(0, {})
        return self._scope

    # def exit(self, *args):
    #     del self.references.maps[0]
    #     if len(args) == 1:
    #         self.references[self.names[-1]] = args[0]
    #     elif len(args) > 1:
    #         raise ValueError("too many arguments given to exit()")
    #     self.names.pop()

    def merge(self, value, referenced, start: TokenInfo):
        if isinstance(referenced, set):
            if not isinstance(value, set):
                raise DataParseError(f"cannot merge {type(value).__name__!r} into {type(referenced).__name__!r}", self.filename, start)
            for elem in referenced:
                value.add(self.copy(elem))
        elif isinstance(referenced, list):
            if not isinstance(value, list):
                raise DataParseError(f"cannot merge {type(value).__name__!r} into {type(referenced).__name__!r}", self.filename, start)
            for elem in referenced:
                value.append(self.copy(elem))
        elif isinstance(referenced, tuple):
            if not isinstance(value, tuple):
                raise DataParseError(f"cannot merge {type(value).__name__!r} into {type(referenced).__name__!r}", self.filename, start)
            value = list(value)
            for elem in referenced:
                value.append(self.copy(elem))
            value = tuple(value)
        elif isinstance(referenced, dict):
            if not isinstance(value, dict):
                raise DataParseError(f"cannot merge {type(value).__name__!r} into {type(referenced).__name__!r}", self.filename, start)
            for key, elem in referenced.items():
                if key not in value:
                    value[key] = self.copy(elem)
        else:
            raise DataParseError(f"cannot merge {type(value).__name__!r} into {type(referenced).__name__!r}", self.filename, start)
        return value

    # ------------------------------------------------------

    def parse_all(self):
        if self.token.type == ENDMARKER:
            return {}
        if self.allow_imports:
            while self.test(('from', 'import')):
                self.parse_import()
        key, value = self.parse_key_value()
        return self._parse_object_rest({(key):value}, indented=None)
    
    def parse_import(self):
        if self.eat('import'):
            packages = {}
            self.parse_import_name_list(packages)
            for package, alias in packages.items():
                module = __import__(package, self.import_globals, self.import_locals)
                # for attr in package.split('.')[1:]:
                #     module = getattr(module, attr)
                if '.' in package:
                    name = package[0:package.index('.')]
                else:
                    name = package
                self.import_globals[name] = module

        elif self.eat('from'):
            package = self.parse_import_name()
            self.expect('import')
            from_names = {}
            if self.eat('('):
                self.parse_import_from_names(from_names)
                self.expect(')')
            else:
                self.parse_import_name_list(from_names)
            imports = __import__(package, self.import_globals, self.import_locals, from_names.keys())
            for name, alias in from_names.items():
                self.import_globals[alias] = getattr(imports, name)
        else:
            raise self.expected(('import', 'from'))

        if not self.eat_newline():
            raise self.expected(NEWLINE)
    
    def parse_import_name(self):
        start = self.token
        name = self.expect(NAME)
        for subname in name.split('.'):
            if not subname.isidentifier() or iskeyword(subname):
                raise DataParseError(f"{name!r} is not a valid import name", self.filename, start)
        return name

    def parse_import_alias(self):
        start = self.token
        name = self.expect(NAME)
        if not name.isidentifier() or iskeyword(name):
            raise DataParseError(f"{name!r} is not a valid import alias", self.filename, start)
        return name

    def parse_import_name_list(self, names: dict):
        while True:
            start = self.token
            name = self.parse_import_name()
            if self.eat('as'):
                start = self.token
                alias = self.parse_import_alias()
                if alias in names or alias in self.import_globals:
                    raise DataParseError(f"duplicate import name {alias!r}", self.filename, start)
                names[name] = alias
            else:
                if name in names or name in self.import_globals:
                    raise DataParseError(f"duplicate import name {name!r}", self.filename, start)
                names[name] = name
            if not self.eat(','):
                break

    def parse_import_from_names(self, from_names: dict):
        indented = self.eat(NEWLINE, INDENT)
        self.skip_blanks()
        start = self.token
        name = self.parse_import_name()
        self.skip_blanks()
        if self.eat('as'):
            self.skip_blanks()
            start = self.token
            alias = self.parse_import_alias()
            if alias in from_names or alias in self.import_globals:
                raise DataParseError(f"duplicate import name {alias!r}", self.filename, start)
            from_names[name] = alias
            self.skip_blanks()
        else:
            if name in from_names or name in self.import_globals:
                raise DataParseError(f"duplicate import name {name!r}", self.filename, start)
            from_names[name] = name
        while self.eat(','):
            self.skip_blanks()
            if indented:
                if self.test(NEWLINE, DEDENT):
                    break
                if self.test(')'):
                    raise DataParseError("invalid closing ')' location", self.filename, self.token)
            elif self.test(')'):
                break
            if self.test(NEWLINE, INDENT):
                self.parse_import_from_names(from_names)
            else:
                start = self.token
                name = self.parse_import_name()
                self.skip_blanks()
                if self.eat('as'):
                    self.skip_blanks()
                    start = self.token
                    alias = self.parse_import_alias()
                    if alias in from_names or alias in self.import_globals:
                        raise DataParseError(f"duplicate import name {alias!r}", self.filename, start)
                    from_names[name] = alias
                    self.skip_blanks()
                else:
                    if name in from_names or name in self.import_globals:
                        raise DataParseError(f"duplicate import name {name!r}", self.filename, start)
                    from_names[name] = name
        if indented:
            self.expect(NEWLINE, DEDENT)

    def parse_imported_type(self):
        start = self.token
        name = self.expect(NAME)
        try:
            return eval(name, self.import_globals, {}), start
        except KeyError:
            raise DataParseError(f"no type {name!r} has been imported", self.filename, start)

    def parse_reference(self):
        start = self.token
        op = self.expect(('@', '*', '**'))
        if self.test(STRING):
            name: str = ast.literal_eval(self.next())
        elif self.test((NAME, NUMBER)):
            name: str = self.next()
        else:
            raise self.expected((NAME, NUMBER, STRING))
        try:
            return self.references[name]
        except KeyError:
            i = name.rfind('.')
            while i != -1:
                left = name[0:i]
                right = name[i+1:]
                if left in self.references:
                    value = self.references[left]
                    def look(name, value):
                        try:
                            i = name.index('.')
                            name2 = name[0:i]
                            try:
                                value2 = value[name2]
                            except TypeError:
                                try:
                                    count = int(name2)
                                except ValueError:
                                    raise KeyError
                                else:
                                    try:
                                        if isinstance(value, set):
                                            value2 = list(value)[count]
                                        else:
                                            value2 = value[count]
                                    except IndexError:
                                        raise KeyError
                            return look(name[i+1:], value2)
                        except ValueError:
                            try:
                                return value[name]
                            except TypeError:
                                try:
                                    count = int(name)
                                except ValueError:
                                    raise KeyError
                                else:
                                    try:
                                        if isinstance(value, set):
                                            return list(value)[count]
                                        else:
                                            return value[count]
                                    except IndexError:
                                        raise KeyError
                    try:
                        return look(right, value)
                    except KeyError:
                        pass
                i = name.rfind('.', 0, i)

            raise DataParseError(f"undefined reference to {name!r}", self.filename, start)

    def parse_key(self):
        if self.token.type == STRING:
            return ast.literal_eval(self.next())
        elif self.token.type in (NAME, NUMBER):
            return self.next()
            # token = self.token
            # key = self.next()
            # if key in (self.true, self.false, self.none, self.ninf, self.nnan) or key in self.inf or key in self.infj or key in self.ninfj or key in self.nan or key in self.nanj or key in self.nnanj:
            #     raise DataParseError(f"illegal unquoted key {key!r}", self.filename, token)
        else:
            raise self.expected(self.key_types)
    
    def parse_value(self):
        if self.test('@'):
            referenced = self.parse_reference()
            start = self.token
            if not self.test(',', '}', ')', ']', ENDMARKER, NEWLINE):
                value = self.parse_value()
                value = self.merge(value, referenced, start)
            else:
                value = self.copy(referenced)
            return value
        elif self.test(NAME, '('):
            return self.parse_explicit_type()
        elif self.test('{'):
            return self.parse_object_or_set()
        elif self.test('['):
            return self.parse_list()
        elif self.test('('):
            return self.parse_tuple()
        else:
            return self.parse_simple_value()

    def parse_inline_value(self):
        if self.test(NAME):
            self.tokens.push_marker()
            self.next()
            has_lparen = self.test('(')
            self.tokens.pop_marker(reset=True)
            if has_lparen:
                return self.parse_inline_explicit_type()
        if self.test('@'):
            referenced = self.parse_reference()
            self.skip_blanks()
            start = self.token
            if not self.test(',', '}', ')', ']', ENDMARKER):
                value = self.parse_inline_value()
                value = self.merge(value, referenced, start)
            else:
                value = self.copy(referenced)
            return value
        elif self.test('{'):
            return self.parse_inline_object_or_set()
        elif self.test('['):
            return self.parse_inline_list()
        elif self.test('('):
            return self.parse_inline_set()
        else:
            return self.parse_simple_value()

    def parse_key_value(self, allow_typed_section_block=True):
        key = self.parse_key()
        self.expect(':')
        with self.enter(key):
            self.value = self._parse_key_value_rest(allow_typed_section_block)
            return key, self.value

    def _parse_key_value_rest(self, allow_typed_section_block=True):
        if allow_typed_section_block and self.test(NAME, NEWLINE, INDENT, self.key_types, ':') or self.test(NAME, NEWLINE, INDENT, ('-', '--', '---', self.num_list_start)):
            imported_type, start = self.parse_imported_type()
            value = self.parse_section_block()
            value = self.finalize_explicit_type(imported_type, start, args=[value], kwargs={})
        elif self.test('@'):
            referenced = self.parse_reference()
            start = self.token
            if not self.test(',', '}', ')', ']', ENDMARKER) and (not self.test(NEWLINE) or self.test(NEWLINE, (INDENT, '-', '--', '---', self.num_list_start))):
                value = self._parse_key_value_rest()
                value = self.merge(value, referenced, start)
            else: 
                value = self.copy(referenced)
        elif self.test(NEWLINE, ('-', '--', '---', '1.')):
            self.expect(NEWLINE)
            value = self.parse_list_block(has_indent=False)
            self.tokens.previous()
        elif self.eat(NEWLINE, INDENT):
            if self.test(self.key_types, ':') or self.test(('**', '--', '-', '---', self.num_list_start)):
                value = self.parse_section_block(ate_indent=True)
            elif self.test('*'):
                raise DataParseError("* not allowed here", self.filename, self.token)
            else:
                value = self.parse_value()
                self.expect(NEWLINE, DEDENT)
        elif self.test(self.key_types, ':'):
            key = self.parse_key()
            self.expect(':')
            with self.enter(key):
                value = self.value = self._parse_key_value_rest()
            value = {key: value}
        elif self.test(NEWLINE, ('{', '(', '[')):
            self.expect(NEWLINE)
            value = self.parse_value()
        else:
            value = self.parse_value()
        return value

    def parse_inline_key_value(self):
        key = self.parse_key()
        self.skip_blanks()
        self.expect(':')
        self.skip_blanks()
        with self.enter(key):
            self.value = self._parse_inline_key_value_rest()
            return key, self.value

    def _parse_inline_key_value_rest(self):
        if self.test('@'):
            referenced = self.parse_reference()
            self.skip_blanks()
            start = self.token
            # if self.test(('{', '[', '(', NAME, NUMBER, STRING, '@')):
            if not self.test((',', '}', ')', ']', ENDMARKER)):
                value = self._parse_inline_key_value_rest()
                value = self.merge(value, referenced, start)
            else: 
                value = self.copy(referenced)
        elif self.test(self.key_types):
            try:
                with self.tokens:
                    self.tokens.push_marker()
                    key = self.parse_key()
                    self.skip_blanks()
                    has_colon = self.eat(':')
            except DataParseError:
                self.tokens.pop_marker(reset=True)
                value = self.parse_inline_value()
            else:
                if has_colon:                    
                    self.tokens.pop_marker(reset=False)
                    with self.enter(key):
                        value = self.value = self._parse_inline_key_value_rest()
                    value = {key: value}
                else:
                    self.tokens.pop_marker(reset=True)
                    value = self.parse_inline_value()
        else:
            value = self.parse_inline_value()
        return value

    def parse_section_block(self, ate_indent=False, obj=None):
        if not ate_indent:
            self.expect(NEWLINE, INDENT)
    
        if self.test(('-', '--', '---', self.num_list_start)):
            return self.parse_list_block(ate_indent=True)

        if self.test('**'):
            start = self.token
            x = self.parse_reference()
            if not isinstance(x, dict):
                raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
            if obj is None:
                obj = self.copy(x)
            else:
                obj.update(x)
        elif self.test('*'):
            raise DataParseError("* not allowed here", self.filename, self.token)
        else:
            if obj is None:
                obj = {}
            start = self.token
            key, value = self.parse_key_value()
            if key in obj:
                raise DataParseError(f"duplicate key {key!r}", self.filename, start)
            obj[key] = value
        return self._parse_section_block_rest(obj)

    def _parse_section_block_rest(self, obj: dict):
        while self.eat_newline():
            if self.test(DEDENT):
                break
            start = self.token
            if self.test('**'):
                x = self.parse_reference()
                try:
                    obj.update(x)
                except TypeError:
                    raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
            elif self.test('*'):
                raise DataParseError("* not allowed here", self.filename, self.token)
            else:
                key, value = self.parse_key_value()
                if key in obj:
                    raise DataParseError(f"duplicate key {key!r}", self.filename, start)
                obj[key] = value
        self.expect(DEDENT)
        return obj

    def parse_list_block(self, ate_indent=False, has_indent=True):
        if not ate_indent and has_indent:
            self.expect(NEWLINE, INDENT)
        if self.eat(self.num_list_start):
            numbered = True
            sep = self.num_list_regex(2)
            index = 2
        else:
            sep = self.expect(('-', '--', '---'))
            numbered = False
        lst = []
        self.parse_list_block_value(lst)
        while self.eat_newline() and self.eat(sep):
            self.parse_list_block_value(lst)
            if numbered:
                index += 1
                sep = self.num_list_regex(index)
        if has_indent:
            self.expect(DEDENT)
        return lst

    def parse_list_block_value(self, lst: list):
        if self.test(NEWLINE):
            lst.append(self.parse_section_block())
        elif self.test(self.key_types, ':'):
            key, value = self.parse_key_value(allow_typed_section_block=False)
            obj = {key: value}
            if self.test(NEWLINE, INDENT):
                obj = self.parse_section_block(obj=obj)
            lst.append(obj)
        elif self.test('**'):
            start = self.token
            x = self.parse_reference()
            if not isinstance(x, dict):
                raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
            obj = self.copy(x)
            if self.test(NEWLINE, INDENT):
                obj = self.parse_section_block(obj=obj)
            lst.append(obj)
        elif self.test('*'):
            start = self.token
            x = self.parse_reference()
            try:
                for elem in x:
                    lst.append(self.copy(elem))
            except TypeError:
                raise DataParseError(f"element after * must be an iterable, not {type(x).__name__!r}", self.filename, start)
        elif self.test(('-', '--', '---')):
            sep = self.expect(('-', '--', '---'))
            lst2 = []
            self.parse_list_block_value(lst2)
            if self.eat(NEWLINE, INDENT):
                self.expect(sep)
                self.parse_list_block_value(lst2)
                while self.eat_newline() and self.eat(sep):
                    self.parse_list_block_value(lst2)
                self.expect(DEDENT)
            lst.append(lst2)
        elif self.test('@'):
            referenced = self.parse_reference()
            start = self.token
            # if not self.test(',', '}', ')', ']', ENDMARKER) and (not self.test(NEWLINE) or self.test(NEWLINE, INDENT)):
            #     value = self._parse_key_value_rest()
            #     value = self.merge(value, referenced, start)
            # else: 
            #     value = self.copy(referenced)
            value = self.copy(referenced)
            lst.append(value)
        else:
            lst.append(self.parse_value())

    def parse_object_or_set(self):
        self.expect('{')
        if self.eat(NEWLINE, INDENT):
            return self._parse_object_or_set_rest(indented=True)
        elif self.eat(NEWLINE):
            return self._parse_object_or_set_rest(indented=False)
        else:
            return self._parse_inline_object_or_set_rest()

    def _parse_object_or_set_rest(self, indented: bool):
        if not indented:
            self.skip_blanks()
            if self.eat('}'):
                return {}
        if self.test('**'):
            start = self.token
            x = self.parse_reference()
            if not isinstance(x, dict):
                raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
            return self._parse_object_rest(self.copy(x), indented)
        if self.test('*') or not self.test(self.key_types, ':'):
            return self._parse_set_rest(set(), indented)
        else:
            key, value = self.parse_key_value()
            return self._parse_object_rest({key: value}, indented)

    def parse_inline_object_or_set(self):
        self.expect('{')
        return self._parse_inline_object_or_set_rest()

    def _parse_inline_object_or_set_rest(self):
        self.skip_blanks()
        if self.eat('}'):
            return {}
        elif self.eat(','):
            self.skip_blanks()
            self.expect('}')
            return set()
        if self.test('**'):
            start = self.token
            x = self.parse_reference()
            if not isinstance(x, dict):
                raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
            return self._parse_inline_object_rest(self.copy(x))
        if self.test('*') or not self.test((self.key_types)):
            return self._parse_inline_set_rest(set())
        self.tokens.push_marker()
        try:
            self.parse_key()
            self.skip_blanks()
            has_colon = self.test((':', '**'))
        except DataParseError:
            self.tokens.pop_marker(reset=True)
            return self._parse_inline_set_rest(set())
        else:
            self.tokens.pop_marker(reset=True)
            if has_colon:
                start = self.token
                if has_colon == '**':
                    x = self.parse_reference()
                    if not isinstance(x, dict):
                        raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                    return self._parse_inline_object_rest(self.copy(x))
                else:
                    key, value = self.parse_inline_key_value()
                    return self._parse_inline_object_rest({key: value})
            else:
                return self._parse_inline_set_rest(set())

    def parse_object(self):
        self.expect('{')
        if self.eat(NEWLINE, INDENT):
            if self.test('**'):
                start = self.token
                x = self.parse_reference()
                if not isinstance(x, dict):
                    raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                return self._parse_object_rest(self.copy(x), indented=True)
            elif self.test('*'):
                raise DataParseError(f"* is not allowed here", self.filename, self.token)
            else:
                key, value = self.parse_key_value()
                return self._parse_object_rest({(key):value}, indented=True)
        elif self.eat(NEWLINE):
            if self.test('**'):
                start = self.token
                x = self.parse_reference()
                if not isinstance(x, dict):
                    raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                return self._parse_object_rest(self.copy(x), indented=False)
            elif self.test('*'):
                raise DataParseError(f"* is not allowed here", self.filename, self.token)
            else:
                key, value = self.parse_key_value()
                return self._parse_object_rest({(key):value}, indented=False)
        else:
            self.skip_blanks()
            if self.test('**'):
                start = self.token
                x = self.parse_reference()
                if not isinstance(x, dict):
                    raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                return self._parse_inline_object_rest(self.copy(x))
            elif self.test('*'):
                raise DataParseError(f"* is not allowed here", self.filename, self.token)
            else:
                key, value = self.parse_inline_key_value()
                return self._parse_inline_object_rest({(key):value})

    def _parse_object_rest(self, obj: dict, indented: bool):
        if indented:
            end_tokens = (DEDENT, '}')
        elif indented is None:
            end_tokens = (ENDMARKER,)
        else:
            end_tokens = ('}',)
        if self.eat(','):
            if not self.test(NEWLINE, *end_tokens):
                if not self.eat_newline():
                    raise self.expected(NEWLINE)
                if indented and self.test('}'):
                    raise DataParseError("invalid closing '}' location", self.filename, self.token)
                start = self.token
                if self.test('**'):
                    x = self.parse_reference()
                    if not isinstance(x, dict):
                        raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                    for key, value in x.items():
                        obj[key] = self.copy(value)
                elif self.test('*'):
                    raise DataParseError("* is not allowed here", self.filename, start)
                else:
                    key, value = self.parse_key_value()
                    if key in obj:
                        raise DataParseError(f"duplicate key {key!r}", self.filename, start)
                    obj[key] = value
                while self.eat(','):
                    if not self.eat_newline():
                        if indented and self.test(NEWLINE, *end_tokens):
                            self.expect(NEWLINE)
                            break
                        else:
                            raise self.expected(NEWLINE)
                    if self.test(*end_tokens):
                        break
                    elif indented and self.test('}'):
                        raise DataParseError("invalid closing '}' location", self.filename, self.token)
                    start = self.token
                    if self.test('**'):
                        x = self.parse_reference()
                        if not isinstance(x, dict):
                            raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                        for key, value in x.items():
                            obj[key] = self.copy(value)
                    elif self.test('*'):
                        raise DataParseError("* is not allowed here", self.filename, start)
                    else:
                        key, value = self.parse_key_value()
                        if key in obj:
                            raise DataParseError(f"duplicate key {key!r}", self.filename, start)
                        obj[key] = value
                else:
                    if indented and self.test(NEWLINE, *end_tokens):
                        self.expect(NEWLINE)
            else:
                self.expect(NEWLINE)
        else:
            while self.eat_newline():
                if self.test(*end_tokens):
                    break
                elif indented and self.test('}'):
                    raise DataParseError("invalid closing '}' location", self.filename, self.token)
                start = self.token
                if self.test('**'):
                    x = self.parse_reference()
                    if not isinstance(x, dict):
                        raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                    for key, value in x.items():
                        obj[key] = self.copy(value)
                elif self.test('*'):
                    raise DataParseError("* is not allowed here", self.filename, start)
                else:
                    key, value = self.parse_key_value()
                    if key in obj:
                        raise DataParseError(f"duplicate key {key!r}", self.filename, start)
                    obj[key] = value

        self.expect(*end_tokens)
        return obj

    def parse_inline_object(self):
        self.expect('{')
        self.skip_blanks()
        if self.eat('}'):
            return {}
        else:
            start = self.token
            if self.test('**'):
                x = self.parse_reference()
                if not isinstance(x, dict):
                    raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                return self._parse_inline_object_rest(self.copy(x))
            elif self.test('*'):
                raise DataParseError("* is not allowed here", self.filename, start)
            else:
                key, value = self.parse_inline_key_value()
                return self._parse_inline_object_rest({(key): value})

    def _parse_inline_object_rest(self, obj: dict):
        self.skip_blanks()
        while self.eat(','):
            self.skip_blanks()
            if self.test('}'):
                break
            start = self.token
            if self.test('**'):
                x = self.parse_reference()
                if not isinstance(x, dict):
                    raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                for key, value in x.items():
                    obj[key] = self.copy(value)
            elif self.test('*'):
                raise DataParseError("* is not allowed here", self.filename, start)
            else:
                key, value = self.parse_inline_key_value()
                if key in obj:
                    raise DataParseError(f"duplicate key {key!r}", self.filename, start)
                obj[key] = value
            self.skip_blanks()
        self.expect('}')
        return obj

    def parse_set(self):
        self.expect('{')
        if self.eat(NEWLINE, INDENT):
            return self._parse_set_rest(set(), indented=True)
        elif self.eat(NEWLINE):
            return self._parse_set_rest(set(), indented=False)
        else:
            return self._parse_inline_set_rest(set())

    def _set_add(self, lst: set, value, start_token):
        if value in lst:
            raise DataParseError(f"duplicate element {value!r}", self.filename, start_token)
        lst.add(value)

    def _parse_set_rest(self, lst: set, indented: bool):
        return self._parse_list_rest(lst, indented, closing_token='}', add=self._set_add)

    def parse_inline_set(self):
        self.expect('{')
        return self._parse_inline_set_rest(set())

    def _parse_inline_set_rest(self, lst: set):
        return self._parse_inline_list_rest(lst, closing_token='}', add=self._set_add)

    def parse_list(self):
        self.expect('[')
        if self.eat(NEWLINE, INDENT):
            return self._parse_list_rest([], indented=True)
        elif self.eat(NEWLINE):
            return self._parse_list_rest([], indented=False)
        else:
            return self._parse_inline_list_rest([])

    def _parse_list_rest(self, lst, indented: bool, closing_token=']', add=lambda lst, value, start_token: lst.append(value)):
        if indented:
            end_tokens = (DEDENT, closing_token)
        else:
            end_tokens = (closing_token,)
        if self.eat(*end_tokens):
            return lst

        prev_start, prev_value = self.parse_list_element(lst, prev_value=None, prev_start=None, add=add)
        if self.eat(','): # Comma-separated list
            if not self.eat_newline():
                raise self.expected(NEWLINE)
            if not self.test(*end_tokens):
                if indented and self.test(closing_token):
                    raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
                prev_start, prev_value = self.parse_list_element(lst, prev_value, prev_start, add)
                if self.eat(','):
                    if not self.eat_newline():
                        raise self.expected(NEWLINE)
                    while True:
                        if self.test(*end_tokens):
                            break
                        if indented and self.test(closing_token):
                            raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
                        prev_start, prev_value = self.parse_list_element(lst, prev_value, prev_start, add)
                        try:
                            if not self.eat(','):
                                break
                        finally:
                            if not self.eat_newline():
                                raise self.expected(NEWLINE)
                else:
                    if not self.eat_newline():
                        raise self.expected(NEWLINE)

        else: # Newline-separated list
            while self.eat_newline():
                if self.test(*end_tokens):
                    break
                if indented and self.test(closing_token):
                    raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
                prev_start, prev_value = self.parse_list_element(lst, prev_value, prev_start, add)

        self.expect(*end_tokens)
        return lst

        #region old method
        # if self.test(self.key_types):
        #     self.tokens.push_marker()
        #     self.next()
        #     if self.test(':'):
        #         self.tokens.pop_marker(reset=True)
        #         start = self.token
        #         key, value = self.parse_key_value()
        #         obj = {(key): value}
        #         add(lst, obj, start)
        #         if self.eat(','):
        #             if not self.eat_newline():
        #                 raise self.expected(NEWLINE)
        #             if not self.test(*end_tokens):
        #                 if indented and self.test(closing_token):
        #                     raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
        #                 start = self.token
        #                 key, value = self.parse_key_value()
        #                 if key in obj:
        #                     obj = {(key): value}
        #                     add(lst, obj, start)
        #                 else:
        #                     obj[key] = value
        #                 if self.eat(','):
        #                     if not self.eat_newline():
        #                         raise self.expected(NEWLINE)
        #                     while True:
        #                         if self.test(*end_tokens):
        #                             break
        #                         elif indented and self.test(closing_token):
        #                             raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
        #                         start = self.token
        #                         key, value = self.parse_key_value()
        #                         if key in obj:
        #                             obj = {(key): value}
        #                             add(lst, obj, start)
        #                         else:
        #                             obj[key] = value
        #                         try:
        #                             if not self.eat(','):
        #                                 break
        #                         finally:
        #                             if not self.eat_newline():
        #                                 raise self.expected(NEWLINE)
        #                 else:
        #                     if not self.eat_newline():
        #                         raise self.expected(NEWLINE)
        #         else:
        #             while self.eat_newline():
        #                 if self.test(*end_tokens):
        #                     break
        #                 elif indented and self.test(closing_token):
        #                     raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
        #                 start = self.token
        #                 key, value = self.parse_key_value()
        #                 if key in obj:
        #                     obj = {(key): value}
        #                     add(lst, obj, start)
        #                 else:
        #                     obj[key] = value
        #         self.expect(*end_tokens)
        #         return lst

        #     else:
        #         self.tokens.pop_marker(reset=True)

        # start = self.token
        # value = self.parse_value()
        # add(lst, value, start)
        # if self.eat(','):
        #     if not self.eat_newline():
        #         raise self.expected(NEWLINE)
        #     if not self.test(*end_tokens):
        #         if indented and self.test(closing_token):
        #             raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
        #         start = self.token
        #         value = self.parse_value()
        #         add(lst, value, start)
        #         if self.eat(','):
        #             if not self.eat_newline():
        #                 raise self.expected(NEWLINE)
        #             while True:
        #                 if self.test(*end_tokens):
        #                     break
        #                 elif indented and self.test(closing_token):
        #                     raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
        #                 start = self.token
        #                 value = self.parse_value()
        #                 add(lst, value, start)
        #                 try:
        #                     if not self.eat(','):
        #                         break
        #                 finally:
        #                     if not self.eat_newline():
        #                         raise self.expected(NEWLINE)
        #         else:
        #             if not self.eat_newline():
        #                 raise self.expected(NEWLINE)
        # else:
        #     while self.eat_newline():
        #         if self.test(*end_tokens):
        #             break
        #         elif indented and self.test(closing_token):
        #             raise DataParseError(f"invalid closing {self._test_str(closing_token)} location", self.filename, self.token)
        #         start = self.token
        #         value = self.parse_value()
        #         add(lst, value, start)
        # self.expect(*end_tokens)
        # return lst
        #endregion

    def parse_list_element(self, lst, prev_value, prev_start, add=lambda lst, value, start_token: lst.append(value)) -> Tuple[TokenInfo, Value]:
        """ Parses an element. This may be either a key: value pair or a normal value. It then adds the element
        to the collection using the given add function.
        
        Args:
            lst (Union[set, list, tuple]): The container object to add to.
            prev_value (Value): The previously parsed element in the list, or the dictionary that we are currently adding key/value pairs to.
            prev_start (TokenInfo): The start token of the previously parsed element.
            add (Callable[[Union[set, list, tuple], Any, TokenInfo], None]): The function which actually adds the value to the collection.
                Parameters are: (lst, value, start) where
                    lst (Union[set, list, tuple]): The container object to add to.
                    value (Value): The value to add.
                    start (TokenInfo): The start token of the value to add.
        
        Returns:
            TokenInfo [0]: The start token of the parsed value.
            Value [1]: The parsed value.
        """
        start = self.token
        with self.enter(len(lst)):
            if self.test(self.key_types, ':'):
                key, value = self.parse_key_value()
                if isinstance(prev_value, dict) and prev_start.type in self.key_types and key not in prev_value:
                    prev_value[key] = value
                    self.value = prev_value
                    return start, prev_value
                else:
                    self.value = {(key): value}
                    add(lst, self.value, start)
                    return start, self.value
            elif self.test('*'):
                x = self.parse_reference()
                try:
                    for elem in x:
                        add(lst, self.copy(elem), start)
                except TypeError:
                    raise DataParseError(f"element after * must be an iterable, not {type(x).__name__!r}", self.filename, start)
                self.value = x
                return start, self.value
            elif self.test('**'):
                raise DataParseError("** is not allowed here", self.filename, start)

            self.value = self.parse_value()
            add(lst, self.value, start)
            return start, self.value

    def parse_inline_list(self):
        self.expect('[')
        return self._parse_inline_list_rest([])

    def _parse_inline_list_rest(self, lst: list, closing_token=']', add=lambda lst, value, start_token: lst.append(value)):
        self.skip_blanks()
        if self.eat(closing_token):
            return lst
        if self.eat(','):
            self.skip_blanks()
            self.expect(closing_token)
            return lst

        prev_start, prev_value = self.parse_inline_list_element(lst, prev_value=None, prev_start=None, add=add)
        self.skip_blanks()
        while self.eat(','):
            self.skip_blanks()
            if self.test(closing_token):
                break
            prev_start, prev_value = self.parse_inline_list_element(lst, prev_value, prev_start, add)
            self.skip_blanks()
        self.expect(closing_token)
        return lst

        #region old method
        # if self.test(self.key_types):
        #     self.tokens.push_marker()
        #     self.next()
        #     if self.test(':'):
        #         self.tokens.pop_marker(reset=True)
        #         start = self.token
        #         key, value = self.parse_inline_key_value()
        #         obj = {(key): value}
        #         add(lst, obj, start)
        #         self.skip_blanks()
        #         while self.eat(','):
        #             self.skip_blanks()
        #             if self.test(closing_token):
        #                 break
        #             start = self.token
        #             key, value = self.parse_inline_key_value()
        #             if key in obj:
        #                 obj = {(key): value}
        #                 add(lst, obj, start)
        #             else:
        #                 obj[key] = value
        #             self.skip_blanks()
        #         self.expect(closing_token)
        #         return lst

        #     else:
        #         self.tokens.pop_marker(reset=True)

        # start = self.token
        # value = self.parse_inline_value()
        # add(lst, value, start)
        # self.skip_blanks()
        # while self.eat(','):
        #     self.skip_blanks()
        #     if self.test(closing_token):
        #         break
        #     start = self.token
        #     value = self.parse_inline_value()
        #     add(lst, value, start)
        #     self.skip_blanks()
        # self.expect(closing_token)
        # return lst
        #endregion

    def parse_inline_list_element(self, lst, prev_value, prev_start, add=lambda lst, value, start_token: lst.append(value)) -> Tuple[TokenInfo, Value]:
        """ Parses an element. This may be either a key: value pair or a normal value. It then adds the element
        to the collection using the given add function.
        
        Args:
            lst (Union[set, list, tuple]): The container object to add to.
            prev_value (Value): The previously parsed element in the list, or the dictionary that we are currently adding key/value pairs to.
            prev_start (TokenInfo): The start token of the previously parsed element.
            add (Callable[[Union[set, list, tuple], Any, TokenInfo], None]): The function which actually adds the value to the collection.
                Parameters are: (lst, value, start) where
                    lst (Union[set, list, tuple]): The container object to add to.
                    value (Value): The value to add.
                    start (TokenInfo): The start token of the value to add.
        
        Returns:
            TokenInfo [0]: The start token of the parsed value.
            Value [1]: The parsed value.
        """
        start = self.token
        with self.enter(len(lst)):
            if self.test(self.key_types):
                self.tokens.push_marker()
                self.next()
                has_colon = self.test(':')
                self.tokens.pop_marker(reset=True)
                if has_colon:
                    key, value = self.parse_inline_key_value()
                    if isinstance(prev_value, dict) and prev_start.type in self.key_types and key not in prev_value:
                        prev_value[key] = value
                        self.value = prev_value
                        return start, prev_value
                    else:
                        self.value = {(key): value}
                        add(lst, self.value, start)
                        return start, self.value
            elif self.test('*'):
                x = self.parse_reference()
                try:
                    for elem in x:
                        add(lst, self.copy(elem), start)
                except TypeError:
                    raise DataParseError(f"element after * must be an iterable, not {type(x).__name__!r}", self.filename, start)
                self.value = x
                return start, self.value
            elif self.test('**'):
                raise DataParseError("** is not allowed here", self.filename, start)

            self.value = self.parse_inline_value()
            add(lst, self.value, start)
            return start, self.value

    def parse_tuple(self):
        self.expect('(')
        if self.eat(NEWLINE, INDENT):
            return self._parse_tuple_rest([], indented=True)
        elif self.eat(NEWLINE):
            return self._parse_tuple_rest([], indented=False)
        else:
            return self._parse_inline_tuple_rest([])

    def _parse_tuple_rest(self, lst: list, indented: bool):
        return tuple(self._parse_list_rest(lst, indented, closing_token=']'))

    def parse_inline_tuple(self):
        self.expect('(')
        return self._parse_inline_tuple_rest([])

    def _parse_inline_tuple_rest(self, lst: list):
        return self._parse_inline_list_rest(lst, closing_token=')')

    def parse_explicit_type(self):
        value, start = self.parse_imported_type()
        self.expect('(')
        if self.eat(NEWLINE, INDENT):
            return self._parse_explicit_type_rest(value, start, indented=True)
        elif self.eat(NEWLINE):
            return self._parse_explicit_type_rest(value, start, indented=False)
        else:
            return self._parse_inline_explicit_type_rest(value, start, inline=False)

    def _parse_explicit_type_rest(self, value, value_start: TokenInfo, indented: bool):
        if indented:
            end_tokens = (DEDENT, ')')
        else:
            end_tokens = (')',)
        args = []
        kwargs = {}
        if not self.test(*end_tokens, looped=True):
            prev_start = prev_value = None
            ate_comma = True
            while not self.test(NAME, '=', looped=True) and not self.test(('*', '**'), looped=True):
                if self.test(*end_tokens):
                    ate_comma = False
                    break
                if indented and self.test(')'):
                    raise DataParseError("invalid closing ')' location", self.filename, self.token)
                prev_start, prev_value = self.parse_list_element(args, prev_value, prev_start)
                try:
                    if not self.eat(','):
                        ate_comma = False
                        break
                finally:
                    if not self.eat_newline():
                        raise self.expected(NEWLINE)

            while ate_comma and self.test('*'):
                start = self.token
                x = self.parse_reference()
                try:
                    args.extend(x)
                except TypeError:
                    raise DataParseError(f"element after * must be an iterable, not {type(x).__name__!r}", self.filename, start)
                try:
                    if not self.eat(','):
                        ate_comma = False
                        break
                finally:
                    if not self.eat_newline():
                        raise self.expected(NEWLINE)

            if ate_comma:
                while True:
                    if self.test(*end_tokens):
                        break
                    if indented and self.test(')'):
                        raise DataParseError(f"invalid closing ')' location", self.filename, self.token)
                    start = self.token
                    if self.test('**'):
                        x = self.parse_reference()
                        try:
                            kwargs.update(x)
                        except TypeError:
                            raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                    else:
                        name = self.expect(NAME)
                        if name in kwargs:
                            raise DataParseError(f"duplicate keyword argument {name!r}", self.filename, start)
                        self.expect('=')
                        def _add(obj, value, start):
                            obj[name] = value
                        self.parse_list_element(kwargs, prev_value=None, prev_start=None, add=_add)
                    try:
                        if not self.eat(','):
                            break
                    finally:
                        if not self.eat_newline():
                            raise self.expected(NEWLINE)
        self.expect(*end_tokens)
        return self.finalize_explicit_type(value, value_start, args, kwargs)

    def parse_inline_explicit_type(self):
        value, start = self.parse_imported_type()
        self.skip_blanks()
        self.expect('(')
        return self._parse_inline_explicit_type_rest(value, start, inline=True)

    def _parse_inline_explicit_type_rest(self, value, value_start: TokenInfo, inline: bool):
        args = []
        kwargs = {}
        if inline:
            parse_list_element = self.parse_inline_list_element
        else:
            parse_list_element = self.parse_list_element
        
        self.skip_blanks()
        if not self.test(')', looped=True):
            prev_start = prev_value = None
            ate_comma = True
            while not self.test(NAME, '=', looped=True) and not self.test(('*', '**'), looped=True):
                if self.test(')'):
                    ate_comma = False
                    break
                prev_start, prev_value = parse_list_element(args, prev_value, prev_start)
                self.skip_blanks()
                if not self.eat(','):
                    ate_comma = False
                    break
                self.skip_blanks()

            while ate_comma and self.test('*'):
                start = self.token
                x = self.parse_reference()
                try:
                    args.extend(x)
                except TypeError:
                    raise DataParseError(f"element after * must be an iterable, not {type(x).__name__!r}", self.filename, start)
                if not self.eat(','):
                    ate_comma = False
                    break
                self.skip_blanks()

            if ate_comma:
                while True:
                    if self.test(')'):
                        break
                    start = self.token
                    if self.test('**'):
                        x = self.parse_reference()
                        try:
                            kwargs.update(x)
                        except TypeError:
                            raise DataParseError(f"element after ** must be a mapping, not {type(x).__name__!r}", self.filename, start)
                    else:
                        name = self.expect(NAME)
                        if name in kwargs:
                            raise DataParseError(f"duplicate keyword argument {name!r}", self.filename, start)
                        self.expect('=')
                        def _add(obj, value, start):
                            obj[name] = value
                        parse_list_element(kwargs, prev_value=None, prev_start=None, add=_add)
                    self.skip_blanks()
                    if not self.eat(','):
                        break
                    self.skip_blanks()
        self.expect(')')
        return self.finalize_explicit_type(value, value_start, args, kwargs)

    def finalize_explicit_type(self, value, value_start: TokenInfo, args: list, kwargs: dict):
        try:
            result = value(*args, **kwargs)
        except Exception as e:
            raise DataParseError(f"exception raised from explicit type constructor", self.filename, value_start) from e
        if isgenerator(result):
            result = list(result)
        return result

    def parse_simple_value(self):
        if self.token.type == NUMBER:
            return self.parse_number_rest(ast.literal_eval(self.next()))
        if self.token.type == STRING:
            return ast.literal_eval(self.next())
        if self.eat(self.true):
            return True
        if self.eat(self.false):
            return False
        if self.eat(self.none):
            return None
        if self.allow_inf_nan:
            if self.eat(self.inf) or self.eat('+', self.inf[0]):
                return self.parse_number_rest(math.inf)
            if self.eat(self.infj) or self.eat('+', (self.infj[0], self.infj[2])):
                return complex(0, math.inf)
            if self.eat(self.ninf):
                return self.parse_number_rest(-math.inf)
            if self.eat(self.ninfj):
                return complex(0, -math.inf)
            if self.eat(self.nan) or self.eat('+', self.nan[0]):
                return self.parse_number_rest(math.nan)
            if self.eat(self.nanj) or self.eat('+', (self.nanj[0], self.nanj[2])):
                return complex(0, math.nan)
            if self.eat(self.nnan):
                return self.parse_number_rest(-math.nan)
            if self.eat(self.nnanj):
                return complex(0, -math.nan)
        if self.token.type == NAME:
            return self.next()
        raise self.expected((NUMBER, STRING, self.true, self.false, self.none, NAME, '{', '[', '('))

    def parse_number_rest(self, value):
        if not isinstance(value, complex):
            if self.token.type == NUMBER and self.token.string[0] in "+-" and self.token.string[-1] in "jJ":
                return value + complex(self.next())
            if self.test('+', NUMBER) and self.tokens.look(1).string[-1] in "jJ":
                self.next()
                return value + complex(self.next())
            if self.test('-', NUMBER) and self.tokens.look(1).string[-1] in "jJ":
                self.next()
                return value - complex(self.next())
            if self.eat(self.pinfj) or self.eat('-', self.ninfj) or self.eat('+', self.infj):
                return complex(value, math.inf)
            if self.eat(self.ninfj) or self.eat('+', self.ninfj):
                return complex(value, -math.inf)
            if self.eat(self.pnanj) or self.eat('-', self.nnanj) or self.eat('+', self.nanj):
                return complex(value, math.nan)
            if self.eat(self.nnanj) or self.eat('+', self.nnanj):
                return complex(value, -math.nan)
        return value

    