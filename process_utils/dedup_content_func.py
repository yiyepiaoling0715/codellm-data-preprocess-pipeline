
import re
import json
import os
from collections import Counter
from process_utils.utils import read_content_with_ignore_error,timeit
from process_utils.algo_utils import hamming_distance,jaccard_distance
from process_utils.constants import Constants,FileterCounter
from process_utils.lang_processor import LangJudge
from process_utils.dedup_content import ContentPattern,DeDupSpan
from functools import partial
from typing import List,Dict,Text
import numpy as np

def judge_bool_useful_by_text(line):
    """
        太短 且是 范围起始标识符,则不去除
    """
    useful_chars=''.join(ContentPattern.pattern_chinese_eng_num_char.findall(line))
    # print('useful_chars=',useful_chars)
    # print(len(useful_chars)<5 , ContentPattern.pattern_useful_arange_symbol.search(line))
    if len(useful_chars)<5 and ContentPattern.pattern_useful_arange_symbol.search(line):
        return True    
    return False

#todo  ts/vue  带有<> 是否也要去重?
def clean_cross_line_of_content(lines:List[Text],filepath):
    """
        代码语义层面的相邻行去重,不考虑 \n\n 这种 多层 这种,  
        需要满足一定的有效字符比例才纳入去重
    """
    #不存在大量重复性相邻行
    if LangJudge.get_language_of_file(filepath=filepath) in [Constants.LANG_PYTHON,Constants.LANG_Go]:
        return lines
    lines_after_filter_cross_line_dedup=[]
    prev_words_per_line_set=set()
    prev_words_per_line_num=-1
    prev_line=''
    index_lines=range(len(lines))
    for tuple_iter in zip(index_lines,lines):
        index_line,line=tuple_iter
        words_per_line=DeDupSpan.split_words(line)
        words_per_line=[word for word in words_per_line if word]
        words_per_line_set=set(words_per_line)
        words_per_line_num=len(list(words_per_line_set))
        #false=>是否需要相似度判断, true=>不需要相似度判断
        bool_useful=False
        if words_per_line_num==0:
            continue
        if index_line==0:
            # prev_words_per_line_set,prev_words_per_line_num,prev_line=words_per_line_set,len(list(words_per_line_set)),line
            bool_useful=True
        bool_useful=judge_bool_useful_by_text(line=line)

        # cocon_words_num=len(list(words_per_line_set.intersection(prev_words_per_line_set)))
        # concon_ratio_precision=cocon_words_num/prev_words_per_line_num
        # concon_ratio_recall=cocon_words_num/words_per_line_num
        concon_ratio_precision,concon_ratio_recall,_=jaccard_distance(set1=prev_words_per_line_set,set2=words_per_line_set)
        if not bool_useful and concon_ratio_precision>0.7 and concon_ratio_recall>0.7:
            if np.random.random()<0.001:
                print(f'行去重 filepath={filepath}\n case 1 上一行={prev_line}\n,去重的当前行cur_line={line}')
            ##mark 在print的下方，要不然会重复
            prev_words_per_line_set,prev_words_per_line_num,prev_line=words_per_line_set,len(list(words_per_line_set)),line
            FileterCounter.counter_dedup_neighbour_line+=1
            continue
        hamming_dist_ratio=hamming_distance(x1=prev_line,x2=line)
        if not bool_useful and hamming_dist_ratio>0.7:
            if np.random.random()<0.001:
                print(f'行去重 filepath={filepath}\n case 2 上一行={prev_line}\n,去重的当前行cur_line={line}')
            ##mark 在print的下方，要不然会重复
            prev_words_per_line_set,prev_words_per_line_num,prev_line=words_per_line_set,len(list(words_per_line_set)),line
            FileterCounter.counter_dedup_neighbour_line+=1
            continue
        # if index_line in [886,887,888,1705,1706,1707,1708,1709,1710,1711]:
        if np.random.random()<0.001 and  index_line in [1532,1533,1533]:
            print(f'index_line={index_line},concon_ratio_precision={concon_ratio_precision},concon_ratio_recall={concon_ratio_recall}')
            print('prev_words_per_line_set=\t',prev_words_per_line_set)
            print('words_per_line_set=\t',words_per_line_set)
            print('-------------------------')
        
        lines_after_filter_cross_line_dedup.append(line)
        prev_words_per_line_set,prev_words_per_line_num,prev_line=words_per_line_set,len(list(words_per_line_set)),line
    
    if len(lines)!=len(lines_after_filter_cross_line_dedup):
        FileterCounter.counter_dedup_neighbour_line_file+=1

    return lines_after_filter_cross_line_dedup
