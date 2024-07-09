"""Extract Python comments (using Python tokenizer) and docstrings (using AST parsing).
   Extract Java and JavaScript comments (using Pygments)"""

import io
from itertools import groupby
from os.path import basename, splitext
import ast
import tokenize
import warnings
import pygments
from pygments.lexers import get_lexer_by_name

StringIO = io.StringIO

NODE_TYPES = {
    ast.ClassDef: "Class",
    ast.FunctionDef: "Function/Method",
    ast.Module: "Module",
}

# comment extraction
def get_comments(s, clean=False):
    "Returns a string including all comments in python code"
    coments = []
    #分词 
    g = tokenize.generate_tokens(StringIO(s).readline)
    for toknum, tokval, _, _, _ in g:
        # print(toknum,tokval)
        if toknum == tokenize.COMMENT:
            coments.append((toknum, tokval))
    result = tokenize.untokenize(coments)
    if clean:
        result = result.replace("#", "")
    return result


# Note: sometimes this can miss examples with decorators over classes
# ast parsing, source: https://gist.github.com/SpotlightKid/1548cb6c97f2a844f72d
def parse_docstrings(source):
    """Parse Python source code and yield a tuple of ast node instance, name,
    and docstring for each function/method, class and module."""
    tree = ast.parse(source)
    ##打印  class,function,module 的  name:text    
    for node in ast.walk(tree):
        if isinstance(node, tuple(NODE_TYPES)):
            docstring = ast.get_docstring(node)
            # print('parse_docstrings getattr(node, "name", None)=',getattr(node, "name", None))
            yield (node, getattr(node, "name", None), docstring)


def get_docstrings(source, module="<string>"):
    """Parse Python source code from file or string and print docstrings."""
    # print('type(source)=',type(source))
    ##??  source  是 text形式??
    if hasattr(source, "read"):
        filename = getattr(source, "name", module)
        module = splitext(basename(filename))[0]
        source = source.read()
    ##??这是个什么排序方式??   source=tuple(node,name,docstring)
    docstrings = sorted(
        parse_docstrings(source), key=lambda x: (NODE_TYPES.get(type(x[0])), x[1])
    )

    grouped = groupby(docstrings, key=lambda x: NODE_TYPES.get(type(x[0])))
    results = []
    for _, group in grouped:
        for _, name, docstring in group:
            name = name if name else module
            # print(docstring or '')
            if docstring:
                results.append(docstring)
    return results


def get_text_python(source, comments=True, clean_comments=True):
    """Extract all natural text in source: comments + docstrings
    the extraction fails in case of syntax errors in the file
    Args:
        source: the code to parse
        comments: if True extract comments two
        clean_comment: if True remove # from extracted comments
    Returns:
        a string with concatenated docstrings and comments"""

    try:
        docstrings = "\n".join(get_docstrings(source))
    except:
        ##如果解析失败,置为空
        docstrings = ""
        warnings.warn(
            "code couldn't be parsed due to compilation failure, no docstring is extracted"
        )

    if comments:
        try:
            comments = get_comments(source, clean=clean_comments)
        except:
            comments = ""
            warnings.warn("tokenization error, no comment is extracted")
    else:
        comments = ""

    output = docstrings + "\n" + comments
    return output.strip()


def comment_size(text, language):
    """
    Compute the size of comments in a program (not necessarily python).
    """
    lexer = get_lexer_by_name(language)
    tokens = pygments.lex(text, lexer)
    comment_len = 0
    for token_type, token in tokens:
        if (
            token_type == pygments.token.Comment.Multiline
            or token_type == pygments.token.Comment.Single
        ):
            comment_len += len(token)  # token is a string with the comment contents
    return comment_len

# #todo 改为基于tree_sitter
def get_nl_ratio(text, language):
    """get the ratio of comments to code in a program"""
    return 0.5
    if language == "python":
        comments = get_text_python(text)
        ratio = len(comments) / len(text)
    else:
        ##todo 优化改进
        try:
            ratio = comment_size(text, language) / len(text)
        except Exception as e:
            ratio = comment_size(text, 'java') / len(text)
    return ratio
