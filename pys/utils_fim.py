

language_properties = {
    'golang': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nfunc',
            '\nimport',
            '\npackage',
        ],
    },
    'python': {
        'comment': '#',
        'stop_words': [
            '\n#',
            '\ndef',
            '\nclass',
            '\nfrom',
            '\nprint', # for phi-1, it always gives a demo like print(fab(5))
        ],
    },
    'javascript': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nfunction',
            '\nimport',
            '\nclass',
        ],
    },
    'typescript': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nfunction',
            '\nimport',
            '\nclass',
            '\ninterface',
            '\ntype',
        ],
    },
    'java': {
        'comment': '//',
        'stop_words': [
            '\n//',
        ],
    },
    'c': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nextern',
            '\ntypedef',
            '\nunion',
            '\nvoid',
        ],
    },
    'cpp': {
        'comment': '//',
        'stop_words': [
            '\n//',
            '\nextern',
            '\ntypedef',
            '\nunion',
            '\nvoid',
            '\nnamespace',
            '\ntemplate',
            '\nusing',
        ],
    },
}

language_alias = {
    'c++': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    'hpp': 'cpp',
    'cppm': 'cpp',
}

for k,v in language_alias.items():
    if k not in language_properties:
        language_properties[k] = language_properties[v]


def gen_language_comment_line(lang: str):
    if not lang:
        return ''
    properties = language_properties.get(lang, {})
    if properties and 'comment' in properties:
        return f'{properties["comment"]} this is {lang} code\n\n'
    return ''


class BaseModel:
    # per model stop words
    stop_words = ['<|endoftext|>', '<s>']

    @staticmethod
    def fim_prompt(prefix, suffix):
        return f'{prefix}<FILL_ME>{suffix}'

    @staticmethod
    def gen_prompt(lang: str, prefix: str, suffix: str=None):
        """
            {prefix}<FILL_ME>{suffix}
        """
        language_line = gen_language_comment_line(lang)
        if language_line:
            prefix = language_line + prefix

        prompt = prefix
        # if prompt is too long, will truncate it, TODO should truncate from new line or new file
        if prompt and len(prompt) > 3500:
            prompt = prompt[-3500:]
        if suffix and hasattr(BaseModel, 'fim_prompt'):
            if len(suffix) >= 1000:
                suffix = suffix[:1000]
            prompt = BaseModel.fim_prompt(prefix, suffix)
        return prompt

