# -*- coding: utf-8 -*-
import tokenize
from io import StringIO

def token_def(text, keywords=('def', 'class')):
    '''
    Tokenizes given string and looks for keywords in the first line.
    Returns the keyword and the index of the end of the definition.
    '''
    tokens = tokenize.generate_tokens(StringIO(text).readline)
    def_type = ''

    for t_type, t_string, t_start, t_end, t_line in tokens:
        if t_type == tokenize.NAME:
            if t_string in keywords:
                def_type = t_string
                break
        elif t_type == tokenize.NL: # no def or class keyword found in current line
            # check if newline is directly at beginning
            return def_type, 0 if t_end == (1, 1) else -1

    counter = 0 # keep record of total characters, needed for newlines
    for t_type, t_string, t_start, t_end, t_line in tokens:
        if t_type == tokenize.OP and t_string == ':':
            return def_type, counter + t_end[1]
        elif t_type == tokenize.NL:
            counter += t_end[1]
    #TODO: find check for 'def f(a,\n\n <other code>'

def token_args(text):
    'Tokenizes given string and returns every name inside two parantheses.'
    tokens = tokenize.generate_tokens(StringIO(text).readline)
    args = []
    for t_type, t_string, t_start, t_end, t_line in tokens:
        if t_type == tokenize.OP and t_string == '(':
            break
        elif t_type == tokenize.NL:
            return
    for t_type, t_string, t_start, t_end, t_line in tokens:
        if t_type == tokenize.NAME:
            args.append(t_string)
        elif t_type == tokenize.OP and t_string == ')':
            break
    return args