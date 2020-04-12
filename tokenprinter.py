from tokenize import *
from typing import Iterable

__all__ = ['print_token', 'print_token_simple', 'token_str', 'simple_token_str',
        'all_token_strs', 'print_tokens']

def print_token(token: TokenInfo):
    print(token_str(token))

def print_token_simple(token: TokenInfo):
    if token.type in (INDENT, DEDENT, ENDMARKER):
        print(tok_name[token.type])
    elif token.type in (NEWLINE, NL):
        print(repr(token.string)[1:-1])
    elif token.type == ENCODING:
        print('ENCODING', repr(token.string))
    elif token.type == STRING and token.string[0]*3 == token.string[0:3]:
        print(token.string[0]*3 + repr(eval(token.string))[1:-1] + token.string[0]*3)
    elif token.type == COMMENT:
        print(token.string.replace('\n', R'\n'))
    else:
        print(token.string)

def token_str(token: TokenInfo):
    return f"{tok_name[token.exact_type]:15} {f'{token.start!r} -> {token.end!r}':30} {token.string!r}"

def simple_token_str(token: TokenInfo):
    if token.type in (INDENT, DEDENT, ENDMARKER):
        return tok_name[token.type]
    elif token.type in (NEWLINE, NL):
        return repr(token.string)[1:-1] or R'\n'
    elif token.type == ENCODING:
        return f"ENCODING {token.string!r}"
    elif token.type == STRING and token.string[0]*3 == token.string[0:3]:
        return token.string[0]*3 + repr(eval(token.string))[1:-1] + token.string[0]*3
    elif token.type == STRING:
        return token.string
    elif token.type == COMMENT:
        return token.string.replace('\n', R'\n')
    else:
        return repr(token.string)

def all_token_strs(tokens: Iterable[TokenInfo]):
    tokens = list(tokens)
    names = [None]*len(tokens)
    stpos = [None]*len(tokens)
    enpos = [None]*len(tokens)
    strs  = [None]*len(tokens)
    longest_name = 0
    longest_spos = 0
    longest_epos = 0

    for i, token in enumerate(tokens):
        name = tok_name[token.exact_type]
        spos = repr(token.start)
        epos = repr(token.end)
        if longest_name < len(name):
            longest_name = len(name)
        if longest_spos < len(spos):
            longest_spos = len(spos)
        if longest_epos < len(epos):
            longest_epos = len(epos)
        if token.type == ENDMARKER:
            string = ''
        elif token.type == INDENT:
            string = R'\t'
        elif token.type == DEDENT:
            string = R'\b'
        elif token.type in (NEWLINE, NL):
            string = R'\n'
        else:
            string = repr(token.string)

        names[i] = name
        stpos[i] = spos
        enpos[i] = epos
        strs[i]  = string

    return [f"{names[i]:{longest_name}} {stpos[i]:{longest_spos}} -> {enpos[i]:{longest_epos}}  {strs[i]}" for i in range(len(names))]

def print_tokens(tokens: Iterable[TokenInfo]):
    print(*all_token_strs(tokens), sep='\n')