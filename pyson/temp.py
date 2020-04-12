import math
from tokenize import *

class DataParseError(SyntaxError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

token: TokenInfo = None
last: TokenInfo = None
filename: str = ''
allow_Infinity_and_NaN = True
python_constants = False
tokens = iter([])

def expect(test):
    result = accept(test)
    if result:
        return result
    else:
        def make_test_str(test):
            if isinstance(test, str):
                return repr(test)
            elif isinstance(test, int):
                return tok_name[test]
            else:
                def expand(t):
                    for elem in t:
                        if isinstance(elem, tuple):
                            yield from expand(elem)
                        else:
                            yield make_test_str(elem)
                return ' or '.join(expand(test))
        raise DataParseError(f'expected {make_test_str(test)}, found {tok_name[token.exact_type]} {token.string!r}', filename, token)

def accept(test):
    result = token.string or True
    if has_next(test):
        proceed()
        return result

def has_next(test):
    return tok_match(token, test)

def tok_match(token, test):
    if isinstance(test, tuple):
        for elem in test:
            if tok_match(token, elem):
                return True
        else:
            return False
    elif isinstance(test, str):
        return token.string == test
    elif isinstance(test, int):
        return token.exact_type == test
    else:
        raise ValueError(f'must be string or int or a tuple thereof, not {type(test).__name__}')

def proceed():
    nonlocal token, last
    try:
        last = token
        token = next(tokens)
        if last is not None:
            return last.string
    except StopIteration as e:
        raise DataParseError(f'unexpected end of token stream', at=(filename, *token.end, token.line)) from e

def skip_blanks():
    nonlocal last
    temp = last
    while token.type in (NEWLINE, INDENT, DEDENT, NL):
        proceed()
    last = temp

# -------------------------------------

#region constants
if python_constants:
    INFINITY = 'inf'
    NAN = 'nan'
    TRUE = 'True'
    FALSE = 'False'
    NONE = 'None'
else:
    INFINITY = 'Infinity'
    NAN = 'NaN'
    TRUE = 'true'
    FALSE = 'false'
    NONE = 'null'
P_INFINITY = '+' + INFINITY
N_INFINITY = '-' + INFINITY
INFINITY_J = INFINITY + 'J'
INFINITY_j = INFINITY + 'j'
P_INFINITY_J = P_INFINITY + 'J'
P_INFINITY_j = P_INFINITY + 'j'
N_INFINITY_J = N_INFINITY + 'J'
N_INFINITY_j = N_INFINITY + 'j'
P_NAN = '+' + NAN
N_NAN = '-' + NAN
NAN_J = NAN + 'J'
NAN_j = NAN + 'j'
P_NAN_J = P_NAN + 'J'
P_NAN_j = P_NAN + 'j'
N_NAN_J = N_NAN + 'J'
N_NAN_j = N_NAN + 'j'

P_INFINITY_Jj = (P_INFINITY_J, P_INFINITY_j)
N_INFINITY_Jj = (N_INFINITY_J, N_INFINITY_j)
P_NAN_Jj = (P_NAN_J, P_NAN_j)
N_NAN_Jj = (N_NAN_J, N_NAN_j)

NUM_CONSTANTS = (INFINITY, P_INFINITY, N_INFINITY, NAN, P_NAN, N_NAN, INFINITY_J, INFINITY_j, P_INFINITY_J, P_INFINITY_j, N_INFINITY_J, N_INFINITY_j, NAN_J, NAN_j, P_NAN_J, P_NAN_j, N_NAN_J, N_NAN_j)
OTHER_CONSTANTS = (TRUE, FALSE, NONE)
#endregion

def parse_key():
    if token.type == STRING:
        result = eval(proceed(), {}, {})
    else:
        last = token
        result = expect((NAME, STRING, NUMBER))
        if allow_Infinity_and_NaN and result in NUM_CONSTANTS or result in OTHER_CONSTANTS:
            raise DataParseError(f"invalid key {result!r}", last, filename)
    return result

def parse_value():
    if token.string == '[':
        return parse_list()
    elif token.string == '{':
        obj = parse_inline_object()
        expect(NEWLINE)
        return obj
    elif token.type == NEWLINE:
        return parse_object(allow_list=True)
    else:
        return parse_simple_value()

def parse_inline_value():
    if token.string == '[':
        return parse_inline_list()
    elif token.string == '{':
        return parse_inline_object()
    else:
        return parse_simple_inline_value()

def parse_simple_value():
    value = parse_simple_inline_value()
    expect(NEWLINE)
    return value  

def parse_number_suffix(result):
    if isinstance(result, (int, float)):
        if token.type == NUMBER:
            if token.string[-1] not in 'jJ':
                raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
            result += eval(proceed(), {}, {})
        elif allow_Infinity_and_NaN:
            if accept(P_INFINITY_Jj):
                result = complex(result, math.inf)
            elif accept(N_INFINITY_Jj):
                result = complex(result, -math.inf)
            elif accept((P_NAN_Jj, N_NAN_Jj)):
                result = complex(result, math.nan)
    return result

def parse_simple_inline_value():
    return parse_simple_inline_value_0(token, proceed, accept)

def parse_simple_inline_value_0(token, proceed, accept):
    if token.type == NUMBER:
        result = eval(proceed(), {}, {})
        if not isinstance(result, complex):
            result = parse_number_suffix(result)
        return result
    # elif token.exact_type == PLUS:
    #     proceed()
    #     if accept(INFINITY):
    #         return math.inf if allow_Infinity_and_NaN else INFINITY
    #     elif accept(NAN):
    #         return math.nan if allow_Infinity_and_NaN else NAN
    #     if token.type != NUMBER:
    #         raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #     return parse_simple_inline_value()
    # elif token.exact_type == MINUS:
    #     proceed()
    #     if accept(INFINITY):
    #         return -math.inf if allow_Infinity_and_NaN else N_INFINITY
    #     elif accept(NAN):
    #         return -math.nan if allow_Infinity_and_NaN else N_NAN
    #     if token.type != NUMBER:
    #         raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #     result = -eval(proceed(), {}, {})
    #     if not isinstance(result, complex) and token.string in ('+', '-'):
    #         neg = token.string == '-'
    #         proceed()
    #         if token.type != NUMBER or token.string[-1] not in 'jJ':
    #             raise DataParseError(f"syntax error at token {tok_name[token.exact_type]}", token, filename)
    #         x = eval(proceed(), {}, {})
    #         if neg:
    #             result -= x
    #         else:
    #             result += x
    #     return result
    elif token.type == STRING:
        return eval(proceed(), {}, {})
    elif accept(TRUE):
        return True
    elif accept(FALSE):
        return False
    elif accept(NONE):
        return None
    elif allow_Infinity_and_NaN and accept((INFINITY, P_INFINITY)):
        return parse_number_suffix(math.inf)
    elif allow_Infinity_and_NaN and accept(N_INFINITY):
        return parse_number_suffix(-math.inf)
    elif allow_Infinity_and_NaN and accept((NAN, P_NAN)):
        return parse_number_suffix(math.nan)
    elif allow_Infinity_and_NaN and token.string == N_NAN:
        proceed()
        return parse_number_suffix(-math.nan)
    elif allow_Infinity_and_NaN and accept((INFINITY_J, INFINITY_j, P_INFINITY_Jj)):
        return complex(0, math.inf)
    elif allow_Infinity_and_NaN and accept(N_INFINITY_Jj):
        return complex(0, -math.inf)
    elif allow_Infinity_and_NaN and accept((NAN_J, NAN_j, P_NAN_Jj)):
        return complex(0, math.nan)
    elif allow_Infinity_and_NaN and accept(N_NAN_Jj):
        return complex(0, -math.nan)
    elif token.type == NAME:
        return proceed()
    else:
        raise DataParseError(f"syntax error at token {tok_name[token.exact_type]} {token.string!r}", token, filename)

def parse_key_value():
    key = parse_key()
    expect(':')
    value = parse_key_value_rest()
    return key, value

def parse_key_value_rest():
    if token.type in (NAME, STRING, NUMBER):
        last_token = token
        proceed()
        if accept(':'):
            if last_token.type == STRING:
                key = eval(last_token.string, {}, {})
            else:
                key = last_token.string
            return { (key): parse_key_value_rest() }
        else:
            called = False
            def _proceed():
                nonlocal called
                if called:
                    return proceed()
                else:
                    called = True
                    return last_token.string
            def _accept(test):
                nonlocal called
                if called:
                    return accept(test)
                elif tok_match(last_token, test):
                    called = True
                    return last_token.string
            return parse_simple_inline_value_0(last_token, _proceed, _accept)
    else:
        return parse_value()

def parse_inline_key_value():
    key = parse_key()
    skip_blanks()
    expect(':')
    skip_blanks()
    last_token = token
    value = parse_inline_value()
    skip_blanks()
    if last_token.type in (NAME, STRING, NUMBER) and accept(':'):
        skip_blanks()
        if last_token.type == STRING:
            key = eval(last_token.string, {}, {})
        else:
            key = last_token.string
        value = { (key): parse_inline_value() }
    
    return key, value

def parse_object(allow_list=False, allow_brackets=True):
    expect(NEWLINE)
    if allow_brackets and token.string == '{':
        obj = parse_inline_object()
        expect(NEWLINE)
        return obj
    elif allow_list and token.string == '[':
        return parse_list()
    expect(INDENT)
    if allow_brackets and token.string == '{':
        obj = parse_inline_object()
        expect(NEWLINE)
        expect(DEDENT)
        return obj
    elif allow_list and token.string == '[':
        lst = parse_list()
        expect(DEDENT)
        return lst
    obj = {}
    while token.type != DEDENT:
        start_token = token
        key, value = parse_key_value()
        if key in obj:
            raise DataParseError(f"duplicate key {key!r}", start_token, filename)
        obj[key] = value
    expect(DEDENT)
    return obj

def parse_inline_object():
    expect('{')
    if token.type == NEWLINE:
        obj = parse_object(allow_brackets=False)
    else:
        skip_blanks()
        obj = {}
        if token.string != '}':
            key, value = parse_inline_key_value()
            obj[key] = value
            skip_blanks()
            if accept(','):
                skip_blanks()
                if token.string != '}':
                    start_token = token
                    key, value = parse_inline_key_value()
                    if key in obj:
                        raise DataParseError(f"duplicate key {key!r}", start_token, filename)
                    obj[key] = value
                    skip_blanks()
                    while accept(','):
                        skip_blanks()
                        if token.string == '}':
                            break
                        start_token = token
                        key, value = parse_inline_key_value()
                        if key in obj:
                            raise DataParseError(f"duplicate key {key!r}", start_token, filename)
                        obj[key] = value
                        skip_blanks()

            elif token.string != '}':
                start_token = token
                key, value = parse_inline_key_value()
                if key in obj:
                    raise DataParseError(f"duplicate key {key!r}", start_token, filename)
                obj[key] = value
                skip_blanks()
                while token.string != '}':
                    start_token = token
                    key, value = parse_inline_key_value()
                    if key in obj:
                        raise DataParseError(f"duplicate key {key!r}", start_token, filename)
                    obj[key] = value
                    skip_blanks()

    expect('}')
    return obj

def parse_list():
    lst = parse_inline_list()
    expect(NEWLINE)
    return lst

def parse_inline_list():
    expect('[')
    lst = []
    skip_blanks()
    if token.string != ']':
        last_token = token
        lst.append(parse_inline_value())
        skip_blanks()
        if last_token.type in (NAME, STRING, NUMBER) and accept(':'):
            skip_blanks()
            obj = {}
            lst.append(obj)
            if last_token.type == STRING:
                key = eval(last_token.string, {}, {})
            else:
                key = last_token.string
            obj[key] = parse_inline_value()
            skip_blanks()
            while token.string != ']' and token.type != ENDMARKER:
                key, value = parse_inline_key_value()
                skip_blanks()
                if key in obj:
                    obj = {}
                    lst.append(obj)
                obj[key] = value

        else:       
            skip_blanks()
            if accept(','):
                skip_blanks()
                if token.string != ']':
                    lst.append(parse_inline_value())
                    skip_blanks()
                    while accept(','):
                        skip_blanks()
                        if token.string == ']':
                            break
                        lst.append(parse_inline_value())
                        skip_blanks()
            
            elif token.string != ']':
                lst.append(parse_inline_value())
                skip_blanks()
                while token.string != ']' and token.type != ENDMARKER:
                    lst.append(parse_inline_value())
                    skip_blanks()

    expect(']')
    return lst

