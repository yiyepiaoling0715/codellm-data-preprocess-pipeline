
"""
    features: ['content', 
        'avg_line_length', 'max_line_length', 'alphanum_fraction', 'size','nl_ratio','repository_name','path','lang',
        'licenses', 
        'index', 'secrets', 
        'fertility_ratio', 'has_secrets', 'number_secrets', 'new_content', 'modified', 'references'],
"""

import re

from collections import Counter
from process_utils.text_extraction import get_nl_ratio
from process_utils.path_utils import content_2_lines,read_code_file_as_list
from process_utils.dedup_content import ContentPattern


def calc_alphanum_ratio(content):
    num_str=''.join(ContentPattern.num_pattern.findall(content))
    alphanum_ratio=len(num_str)/len(content)
    return alphanum_ratio


#耗时
def calc_val_about_len_columns(content,language):
    ##todo 改为 \n split的方法，此方法char num mismatch
    # lines=content_2_lines(content=content)
    lines=content.split('\n')
    lens=[len(line) for line in lines]
    lines_num=len(lines)
    max_line_length=max(lens)
    avg_line_length=sum(lens)/len(lens)
    alphanum_ratio=calc_alphanum_ratio(content=content)
    size=len(content)
    if language:
        comments_ratio=get_nl_ratio(content, language.lower())
    else:
        #todo 改进
        comments_ratio=-1
    word_2_counter_dict=Counter(ContentPattern.space_pattern.split(content))
    word_counter_tuple_desc=sorted(word_2_counter_dict.items(),key=lambda x:x[1],reverse=True)
    return {
            'avg_line_length':int(avg_line_length),
            'max_line_length':int(max_line_length),
            'lines_num':lines_num,
            'alphanum_ratio':round(alphanum_ratio,5),
            'size':size,
            'comments_ratio':round(comments_ratio,5),
            'lines':lines,
            'top5_word_counter':word_counter_tuple_desc[:5]
            }

def calc_feature_of_conent(content,language):
    len_val_dict:Dict=calc_val_about_len_columns(content,language)
    for key,value in len_val_dict.items():
        if isinstance(value,list):
            len_val_dict[key]=str(value)
    if 'lines' in len_val_dict:
        len_val_dict.pop('lines')
    return len_val_dict