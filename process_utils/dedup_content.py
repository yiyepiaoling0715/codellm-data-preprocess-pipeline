
import re
import json
import os
from collections import Counter
from process_utils.utils import read_content_with_ignore_error,timeit
from process_utils.algo_utils import hamming_distance,jaccard_distance
from process_utils.constants import Constants,FileterCounter
from process_utils.lang_processor import LangJudge
from functools import partial
from typing import List,Dict,Text
import numpy as np

def replace_repeat_span(match):
    span = match.group(2)  # 获取重复的字符
    count = match.group(1).count(span)  # 获取这两个字符重复的次数
    # if span in [' ','\t']:
    if DeDupSpan.pattern_only_space_tab.fullmatch(span):
        return span*count
    return f'<|MULTI-{count}-{span}|>'

def replace_same_type_span(char_type,match):
    # span = match.group(2)  # 获取重复的字符
    # count = match.group(1).count(span)  # 获取这两个字符重复的次数
    # print('2 1 0',match.group(2),match.group(1),match.group(0))
    chars = match.group(0)
    num_chars=len(chars)
    return f'<|MULTI-{char_type}-{num_chars}|>'
#todo add , finegtrained replace
partial_number_replace_same_type_span=partial(replace_same_type_span,'number')
# partial_string_replace_same_type_span=partial(replace_same_type_span,'string')
##todo 限制在 test文件
partial_lower_string_replace_same_type_span=partial(replace_same_type_span,'upperstring')
partial_upper_string_replace_same_type_span=partial(replace_same_type_span,'lowerstring')

def hex_to_decimal(match):
    # 十六进制字符串转为十进制
    # print('match.group()',[match.group(1)])
    return '<|HEX-'+str(int(match.group(1), 16))+'|>'

# def replace_hex_with_decimal(text):
#     # 将十六进制替换为十进制
#     return hex_pattern.sub(hex_to_decimal, text)

class ContentPattern:
    print_pattern=re.compile('(print|log|cout|write|say|echo|put|inspect|console|output|cat|http)')
    num_pattern = re.compile(r'\d+')
    space_pattern=re.compile('[\t ]+')

    pattern_chinese_eng_num_char=re.compile('[\u4e00-\u9fa5a-zA-Z0-9]+')
    pattern_useful_char=re.compile('[\u4e00-\u9fa5a-zA-Z0-9_;,\[\]\(\)\{\}]+')
    pattern_null=re.compile('[\r\n \t]+')

    pattern_useful_arange_symbol=re.compile('[{}<>]+')

class DeDupSpanForSft(object):
    pattern_bracketline=re.compile('[\n]{2,}',flags=re.M)
    pat_rep_dict={
        #没必要标记multi，直接替换
        pattern_bracketline:'\n',
    }

    @staticmethod
    @timeit
    def clean_text_by_re(text,filepath=None):
        new_text=text
        for src_pat_iter,dst_rep_symbol_iter in DeDupSpanForSft.pat_rep_dict.items():
            new_text_1=src_pat_iter.sub(dst_rep_symbol_iter,new_text)
            new_text=new_text_1
        return new_text

class DeDupSpan(object):
    #not used
    # pattern_space_1=re.compile('[\t ]+\n')
    pattern_camel_split_words=re.compile('[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)',flags=re.MULTILINE)

    #used
    pattern_test=re.compile('(test|Test|TEST)')
    #函数内换行标志
    pattern_line_bracket_in_function_1=re.compile('([a-zA-Z\)\:"]{2,})([\t]{2,}|[ ]{8,})[a-zA-Z]{2,}')
    pattern_line_bracket_in_function_2=re.compile('(\{|\};|\);|;)([\t]{2,}|[ ]{8,})[a-zA-Z]{2,}')
    

    pattern_split_words_2=re.compile('[\t \n_]+')
    # pattern_split_words_2=re.compile('[\t \n_\{\}\(\)]+')  #影响 {} 这些有意义的符号
    pattern_english=re.compile('[A-Za-z]+')
    
    pattern_asterisk_minus_plus=re.compile('[\*\-+]{5,}')

    pattern_asterisk=re.compile('[\*]{3,}',flags=re.M)
    pattern_centerline=re.compile('[\-]{3,}',flags=re.M)
    pattern_euqalsign=re.compile('[=]{3,}',flags=re.M)
    pattern_poundsign=re.compile('[#]{3,}',flags=re.M)
    pattern_slash=re.compile('[/]{3,}',flags=re.M)
    pattern_bracketline=re.compile('[\n]{3,}',flags=re.M)
    # pattern_array=re.compile('[0-9,]')
    pattern_array=re.compile("\[(\d+,?\s?)+\]")
   
    # pattern_pure_space=re.compile('[\t ]{3,}')
    #错误， \n后面的也给匹配替换了
    # pattern_pure_space = re.compile('(?<!^)(?<!\n)[\t ]{3,}',flags=re.M)
    pattern_pure_space = re.compile( r'(?<=\S)[\t ]+')
    pattern_only_space_tab=re.compile('[\t ]+')
    # 匹配十六进制数字的正则表达式     #先后顺序
    pattern_hex = re.compile(r'(?:\b|\t|\n)(0[xX][0-9a-fA-F]+)[U]*(?:L|l|)(?:\b|\t|\n)')
    pattern_number=re.compile("(?<!HEX-)[0-9]{10,}")
    # pat_float_array=re.compile(r'(\b\d+\.\d+f\b[\s,]*){2,}')
    pattern_float_array=re.compile(r'(\b\d+\.[0-9]{5,}f\b[\s,]*){2,}')
    pattern_float=re.compile('[0-9]+\.[0-9f]{5,}')

    # pattern_many_zero=re.compile('[0,\n]{10,}')
    pattern_many_zero = re.compile(r'(([0,\n]{1,3})\2{5,})')

    pattern_same_chars = re.compile(r'((.)\2{5,})')
    # pattern_tuple_same_chars = re.compile(r'((.)\2{5,})')
    pattern_tuple_same_chars = re.compile(r'((..)\2{5,})')
    pattern_triple_same_chars = re.compile(r'((...)\2{5,})')
    
    pattern_pure_eng_string=re.compile(r"(\"|\')[a-zA-Z]{10,}(\"|\')")
    #不可 逆向
    #必须 有 ""''
    pattern_pure_upper_eng_string=re.compile(r"(\"|\')[A-Z ]{20,}(\"|\')")
    pattern_pure_number_string=re.compile(r"(\"|\')[0-9 ]{10,}(\"|\')")
    pattern_pure_lower_eng_string=re.compile(r"(\"|\')[a-z ]{20,}(\"|\')")
    pattern_pure_hex_string = re.compile(r'(\\x[0-9A-Fa-f]{2})+')

    # 在多行模式下使用 re.M，用于处理多行文本
    # re.sub 将匹配的部分替换为捕获组中的第一个匹配项 (\1)，也就是第一个重复的行
    pattern_same_line = r'^(.{5,})(\n\1)+$'

    pat_rep_dict={
        #必须这么替换, 常规的pattern_same_chars无法识别
        pattern_asterisk:'*',
        pattern_centerline:'-',
        #可以被常规的pattern_same_chars识别
        # pattern_euqalsign:'=',
        # pattern_poundsign:'#',
        # pattern_slash:'/',

        #没必要标记multi，直接替换
        pattern_bracketline:'\n',
        #在pattern_same_chars 的前面
        #不需要替换,tokenizer包含所有的space的处理
        # pattern_pure_space:'\t',
        
        pattern_hex:hex_to_decimal,
        #pattern_same_chars 已经包括了全0的场景
        # pattern_many_zero:replace_repeat_span,
        
        # pattern_same_chars:'<MULTI'+r'\2'+'>',
        # pattern_same_chars:replace_repeat_1_chars,
        pattern_same_chars:replace_repeat_span,
        pattern_tuple_same_chars:replace_repeat_span,
        pattern_triple_same_chars:replace_repeat_span,

        pattern_pure_hex_string: '<|MULTIHEX|>'
    }

    pat_rep_dict_of_restrict={
        # ##todo 改为 检测文件路径是否包含 testcase
        # pattern_pure_upper_eng_string: '<|MULTIUPPERSTRING|>',
        # pattern_pure_lower_eng_string:'<|MULTILOWERSTRING|>',
        # pattern_pure_number_string:'<|MULTINUMBERSTRING|>',

        pattern_array:'<|MULTIARRAY|>',
        pattern_number:'<|MULTINUM|>',
        pattern_float_array:'<|MULTIFLOAT|>',
        pattern_float:'<|FLOAT|>',

        pattern_many_zero:'<MULTIZERO>',
        pattern_pure_upper_eng_string:partial_upper_string_replace_same_type_span,
        pattern_pure_lower_eng_string:partial_lower_string_replace_same_type_span,
        pattern_pure_number_string:partial_number_replace_same_type_span,
    }

    ##统计每种pattern char级别的数量
    pat_rep_2_counter_dict_of_restrict={key:0 for key in list(pat_rep_dict_of_restrict.keys())}
    pat_rep_2_counter_dict=            {key:0 for key in list(pat_rep_dict.keys())}
    ##??  deprecated?
    pat_rep_2_counter_dict.update({pattern_pure_space:0})
    pat_rep_2_counter_dict.update(pat_rep_2_counter_dict_of_restrict)

    all_pat_rep_2_counter=0

    @staticmethod
    @timeit
    def clean_text_by_re(text,filepath=None):
    # def sub_consecutive_symbols(text):
        new_text=text
        for src_pat_iter,dst_rep_symbol_iter in DeDupSpan.pat_rep_dict.items():
            new_text_1=src_pat_iter.sub(dst_rep_symbol_iter,new_text)
            DeDupSpan.pat_rep_2_counter_dict[src_pat_iter]+=len(new_text)-len(new_text_1)
            new_text=new_text_1
        # if new_text.count('test')>5:
        # test_num=DeDupSpan.pattern_test.findall(new_text)
        # if len(test_num)>5:
        # test_num=DeDupSpan.pattern_test.findall(filepath)
        if filepath:
            ##todo 加以优化,处理 filepath_list的情况
            try:
                if isinstance(filepath,list):
                    assert len(filepath)==1
                    filepath=filepath[-1]
                test_num=len(DeDupSpan.pattern_test.findall(filepath))
            except TypeError as e:
                # print(f'filepath={filepath}')
                raise ValueError(f'clean_text_by_re error filepath={filepath}')
            except AssertionError as e:
                print(f'AssertionError filepath={filepath}')
                # raise ValueError(f'filepath数量！=1  error filepath={filepath}')
                test_num=0
            if test_num>0:
                if np.random.random()<0.01:
                    print(f'filepath={filepath},test_num={len(DeDupSpan.pattern_test.findall(filepath))}')
                for src_pat_iter,dst_rep_symbol_iter in DeDupSpan.pat_rep_dict_of_restrict.items():
                    new_text_1=src_pat_iter.sub(dst_rep_symbol_iter,new_text)
                    DeDupSpan.pat_rep_2_counter_dict[src_pat_iter]+=len(new_text)-len(new_text_1)
                    new_text=new_text_1
        new_text_2=re.sub(DeDupSpan.pattern_same_line, r'\1', new_text, flags=re.M | re.I)
        del_len1=len(new_text_2)-len(new_text)
        DeDupSpan.pat_rep_2_counter_dict[DeDupSpan.pattern_same_line]=del_len1
        new_text=new_text_2
        del_len=len(new_text)-len(text)
        DeDupSpan.all_pat_rep_2_counter+=abs(del_len)
        return new_text


    @staticmethod
    def split_camel_method(token:str):
        """
            根据驼峰切词
        """
        sub_tokens=[]
        cur_token=''
        counter=0
        for index_char in range(len(token)-1):
            char_iter=token[index_char]
            if char_iter.isupper() and token[index_char+1].islower():
                sub_tokens.append(cur_token)
                cur_token=char_iter
            else:
                cur_token+=char_iter
        cur_token+=token[-1]
        sub_tokens.append(cur_token)
        assert ''.join(sub_tokens)==token,print('token=',token,'sub_tokens=',sub_tokens)
        return sub_tokens

    @staticmethod
    def split_words(text):
        tokens=DeDupSpan.pattern_split_words_2.split(text)
        # 然后进一步处理每个token，按照驼峰命名法分割
        camel_case_tokens = []
        for token in tokens:
            # 使用正则表达式找到驼峰命名中的分界位置
            if DeDupSpan.pattern_english.match(token):
                # sub_tokens = re.findall(pattern_camel_split_words, token)
                sub_tokens=DeDupSpan.split_camel_method(token=token)
            else:
                sub_tokens=[token]
            camel_case_tokens.extend(sub_tokens)
        return camel_case_tokens

    @staticmethod
    @timeit
    def find_consecutive_chars(text,bool_clean=True):
        """
            为了统计 word counter
        """
        # print(f'find_consecutive_chars 执行正则前 len(text)={len(text)}')
        # text=DeDupSpan.pattern_space_2.sub(' ',text)
        # print(f'find_consecutive_chars 执行正则{DeDupSpan.pattern_space_2} 后,len(text)={len(text)}')
        # text=DeDupSpan.pattern_space_3.sub(' ',text)
        # print(f'find_consecutive_chars 执行正则{DeDupSpan.pattern_space_3} 后,len(text)={len(text)}')
        if bool_clean:
            new_text=DeDupSpan.clean_text_by_re(text=text)
        else:
            new_text=text
        
        counter=Counter()
        consec_span_2_counter={}
        cur_consec_span=''
        bool_in_consec=False
        last_char=''
        i=0
        for char_iter in new_text:
            if char_iter==last_char:
                bool_in_consec=True
                cur_consec_span+=new_text[i]
            else:
                last_char=char_iter
                bool_in_consec=False
                if  len(cur_consec_span)>1:
                    counter[cur_consec_span]+=1           
                cur_consec_span=''
                # if cur_consec_span:
                #     if consec_span_2_counter.get(cur_consec_span):
                #         consec_span_2_counter[cur_consec_span]=0
                    # consec_span_2_counter[cur_consec_span]+=1
            # if i>0 and i%1000000==0:
            #     # consec_span_2_counter_reverse=sorted(counter.items(),key=lambda:x[1],reverse=True)
            #     print('index=',i)
            #     for iterow in counter.most_common(n=100):
            #         print([iterow[0]])
            #         print(iterow[1])
            #         print('============================')
            i+=1
        char_2_counter_dict={k:v for k,v in counter.items() if v>5}
        return char_2_counter_dict

    @staticmethod
    @timeit
    def count_words(text,filepath=None,bool_clean=False):
        """
            统计 word counter,后续 更新tokenizer用
            filepath 只是为了打印标记,不参与数据读取
        """
        if bool_clean:
            # text=DeDupSpan.pattern_space_2.sub(' ',text)
            text_1=DeDupSpan.clean_text_by_re(text=text)
            print(f'count_words 执行正则函数sub_consecutive_symbols 前,len(text)={len(text)},执行正则后,len(text_1)={len(text_1)}')
        else:
            text_1=text
        # text=DeDupSpan.pattern_space_3.sub(' ',text)
        # words=DeDupSpan.pattern_space_2.split(text)
        words_1=DeDupSpan.split_words(text=text_1)
        words=words_1
        len_thres_2_word_freq_dict={}
        left_range=list(range(1,41,5))
        right_range=list(range(6,46,5))
        right_range[-1]=1000
        area_list=list(zip(left_range,right_range))
        if filepath:
            print(f'filepath={filepath}')
        # for len_iter in range(5,40,5):
        for area_iter in area_list:
            left_area=area_iter[0]
            right_area=area_iter[1]
            cur_words=[elem for elem in words if right_area>=len(elem)>left_area]
            cur_counter=Counter(cur_words)
            # most_common_word_freq_dict=cur_counter.most_common(n=50)
            # if most_common_word_freq_dict and most_common_word_freq_dict[0][1]>50:
            #     print(f'*****************area_iter={area_iter}****filepath={filepath}***top1 freq>50**********')
            #     for iterow in most_common_word_freq_dict:
            #         print(iterow)
            cur_counter_trunc={k:v for k,v in cur_counter.items() if v>10}
            len_thres_2_word_freq_dict[left_area]=cur_counter_trunc
        return len_thres_2_word_freq_dict

    @staticmethod
    @timeit
    def find_char_and_words_from_file(filepath,write_dirpath,bool_clean=False):
        if os.path.isdir(filepath):
            print(f'是个目录,find_char_and_words_from_file暂不处理,filepath={filepath}')
            return False
        # with open(filepath,'r') as fr:
        #     text=fr.read()
        content=read_content_with_ignore_error(filepath=filepath)
        if not content:
            return False
        char_2_counter_dict=char_freq_dict=DeDupSpan.find_consecutive_chars(text=content,bool_clean=bool_clean)
        len_thres_2_word_freq_dict=DeDupSpan.count_words(text=content,filepath=filepath)
        filename='_'.join(filepath.split('/')[-3:])
        filepath=os.path.join(write_dirpath,filename)
        with open(filepath,'w') as fw:
            merge_dict={
                'char':char_2_counter_dict,
                'span':len_thres_2_word_freq_dict
            }
            json.dump(merge_dict,fw,ensure_ascii=False,indent=4)

    @staticmethod
    @timeit
    def find_char_and_words_from_jsonfile(filepath,write_dirpath,bool_clean=False):
        content=''
        try:
            with open(filepath,'r') as fr:
                for line in fr:
                    info_dict_iter=json.loads(line)
                    content_iter=info_dict_iter['content']
                    content+=content_iter
        except Exception as e:
            print(f'ERROR find_char_and_words_from_jsonfile 发生异常,filepath={filepath},e={e}')            
            return False
        char_2_counter_dict=char_freq_dict=DeDupSpan.find_consecutive_chars(text=content,bool_clean=bool_clean)
        len_thres_2_word_freq_dict=DeDupSpan.count_words(text=content,filepath=filepath,bool_clean=bool_clean)
        filename='_'.join(filepath.split('/')[-3:])
        write_filepath=os.path.join(write_dirpath,filename)
        with open(write_filepath,'w') as fw:
            merge_dict={
                'char':char_2_counter_dict,
                'span':len_thres_2_word_freq_dict
            }
            json.dump(merge_dict,fw,ensure_ascii=False,indent=4)    

    @staticmethod
    def merge_sub_word_counter_files(src_dirpath,dst_jsonpath):
        char_2_counter_dict_inall={}
        len_thres_2_word_freq_dict_inall={}
        files=os.listdir(src_dirpath)
        for file in files:
            filepath=os.path.join(src_dirpath,file)
            with open(filepath,'r') as fr:
                try:
                    info_dict=json.load(fr)
                # except json.decoder.JSONDecodeError as e:
                except Exception as e:
                    print(f'merge_sub_word_counter_files 文件没有读取成功,e={e.args}, \nfilepath={filepath}')
                    # raise ValueError(f'error  filepath={filepath},e={e}')
                    continue
                char_2_counter_dict=info_dict['char']
                for k,v in char_2_counter_dict.items():
                    if k not in char_2_counter_dict_inall.keys():
                        char_2_counter_dict_inall[k]=0
                    char_2_counter_dict_inall[k]+=v
                len_thres_2_word_freq_dict=info_dict['span']
                for len_thres_iter,word_freq_dict_iter in len_thres_2_word_freq_dict.items():
                    if len_thres_iter not in len_thres_2_word_freq_dict_inall.keys():
                        len_thres_2_word_freq_dict_inall[len_thres_iter]={}
                    for word_iter,freq_iter in word_freq_dict_iter.items():
                        if word_iter not in len_thres_2_word_freq_dict_inall[len_thres_iter].keys():
                            len_thres_2_word_freq_dict_inall[len_thres_iter][word_iter]=0
                        len_thres_2_word_freq_dict_inall[len_thres_iter][word_iter]+=freq_iter
        len_thres_2_word_freq_dict_inall_desc={}
        for len_thres_iter,word_freq_dict_iter in len_thres_2_word_freq_dict_inall.items():
            len_thres_2_word_freq_dict_inall_desc[len_thres_iter]=sorted(word_freq_dict_iter.items(),key=lambda x:x[1],reverse=True)
        char_2_counter_dict_inall_desc=sorted(char_2_counter_dict_inall.items(),key=lambda x:x[1],reverse=True)
        with open(dst_jsonpath,'w') as fw:
            merge_dict={
                'char':char_2_counter_dict_inall_desc,
                'span':len_thres_2_word_freq_dict_inall_desc
            }
            json.dump(merge_dict,fw,ensure_ascii=False,indent=4)

    @staticmethod
    def print():
        # print(f'DeDupSpan.pat_rep_2_counter_dict={DeDupSpan.pat_rep_2_counter_dict}')
        print('**********DeDupSpan.pat_rep_2_counter_dict=*********')
        for k,v in DeDupSpan.pat_rep_2_counter_dict.items():
            print(f'{k}={v}')
        # print(f'DeDupSpan.all_pat_rep_2_counter={DeDupSpan.all_pat_rep_2_counter}')
        print('**********DeDupSpan.all_pat_rep_2_counter=*********')        
        print(DeDupSpan.all_pat_rep_2_counter)
        # for k,v in DeDupSpan.all_pat_rep_2_counter.items():
        #     print(f'{k}={v}')

    @staticmethod
    def _find_split_parts(line:Text,pattern_list:List[re.Pattern]):
        parts=[]    
        for pattern_iter in pattern_list:
            searcher=pattern_iter.search(line)
            if searcher:
                prev_start=0
                for m in pattern_iter.finditer(line):
                    # start=m.start()
                    # print('searcher2=',m.start(),'span1',m.span(1),'span2',m.span(2))
                    # if ':' in line:
                    #     print('index',line.index(':'))
                    cur_start=m.span(2)[0]
                    # print(f'space span={m.span(2)},m={m}')
                    # print([line[:cur_start],line[m.span(2)[0]:]])
                    part_iter=line[prev_start:cur_start]
                    # print('part=',[part_iter])
                    parts.append(part_iter)
                    prev_start=cur_start
                if prev_start<len(line) and prev_start!=0:
                    part_iter=line[prev_start:]
                    # print('part last=',[part_iter,])
                    parts.append(part_iter)
                break
        return parts

    @staticmethod
    def split_line_by_space(line:Text,lang):
        # searcher1=DeDupSpan.pattern_line_bracket_in_function_1.search(line)
        pattern_list=[DeDupSpan.pattern_line_bracket_in_function_2]
        parts=DeDupSpan._find_split_parts(line=line,pattern_list=pattern_list) 
        if not parts and lang in [Constants.LANG_PYTHON]:
            pattern_list_1=[DeDupSpan.pattern_line_bracket_in_function_1,]
            parts=DeDupSpan._find_split_parts(line=line,pattern_list=pattern_list_1) 

        return parts
    
    @staticmethod
    def split_line_by_space_and_add_linebracket(line:Text,lang):
        parts=DeDupSpan.split_line_by_space(line=line,lang=lang)
        if parts:
            new_line_with_linebracket='\n'.join(parts)
            return new_line_with_linebracket
        return line
        
class FunctionPattern:
    # clean_function_bracket_pattern=re.compile(r'(\s*def\s+\w+\s*\(.*?\):\s*)')    
    clean_function_bracket_pattern=re.compile(r'([A-Za-z0-9_]+)\((.|\n)*?\)',flags=re.MULTILINE)    
    suffix_bracket_pattern=re.compile('\((.|\n)*?\)',flags=re.MULTILINE)
    suffix_num_pattern_for_func_text=re.compile(r'_\d+$')
    
    prefix_test_pattern=re.compile('^(TestCase_|TESTCASE_|testcase_|test)(_|)')
    suffix_text_num_pattern=re.compile('(_|)[0-9]+$')
    # TestCase_MCAL_FLS_005
    # trans_testcase_signature_pattern=re.compile('(TestCase_|TESTCASE_|testcase_|test)*([A-Za-z0-9_]+)(_[0-9]+)*')
    trans_testcase_signature_pattern_of_prefix=re.compile('^(TestCase_|TESTCASE_|testcase_|test)([A-Za-z0-9_]+)')
    # trans_testcase_signature_pattern_of_suffix=re.compile('([A-Za-z0-9_]+)(_[0-9]+)$')
    # trans_testcase_signature_pattern_of_suffix=re.compile('([A-Za-z0-9_]+)([0-9]{1,})$')
    trans_testcase_signature_pattern_of_suffix=re.compile('([A-Za-z0-9_]+)(\d+)$')

    @staticmethod
    def clean_node_text(node_text):
        """
            del bracket
        """
        node_text_no_bracket=FunctionPattern.suffix_bracket_pattern.sub('',node_text)
        return node_text_no_bracket

    def batch_clean_node_text(node_text_list):
        text_list=[text for text in node_text_list if text]
        clean_text_list=[FunctionPattern.clean_node_text(text) for text in text_list]
        return clean_text_list

class CommonPattern:
    extract_depend_path_pattern=re.compile('#line.*"(.*)"')
    general_import_pattern=re.compile('(include|from|import|require)[ \t:,]+')
    # general_import_keywords_pattern=re.compile('(include|from|import|require)+')
    # general_import_keywords_pattern=re.compile('(include|from|import|require)+( |\t)')
    # general_import_keywords_pattern=re.compile(r'[include|from|import|require]+[ |\t]+',flags=re.MULTILINE)
    general_import_keywords_pattern=re.compile(r'(?:include|from|import|require)+[ |\t]+',flags=re.MULTILINE)

    import_as_pattern=re.compile('[ \t]+(as|AS)[ \t]+')
    import_common_replace_pattern=re.compile(',[\t \n]+\)')


if __name__=='__main__':
    # path='/xxx/volumes/sc-ep-ulan/llm_data_clean/0414/repo_graph_repos_with_calc/json/train/./datasets-zhineng-os_data_a_srdg_vcp_mvbs_autosar_tc397_fsd__a_srdg_vcp_mvbs_autosar_tc397_fsd_001.json'
    path='/lpai/volumes/sc-ep-ulan/llm_data_clean/0414/repo_graph_repos_with_calc/json/train/datasets-os_data_a_srdg_os_vcos_vcos_mcal_tc3xx__a_srdg_os_vcos_vcos_mcal_tc3xx_002.json'
    dds_obj=DeDupSpan()
    content=open(path).read()
    counter=dds_obj.find_consecutive_chars(content)
    most_common_spans=counter.most_common(n=20)
    for iterow in most_common_spans:
        print(iterow)
    print('*************************')
    # consec_span_2_counter_reverse=sorted(consec_span_2_counter.items(),key=lambda:x[1],reverse=True)
    counter=dds_obj.count_words(content)
    # for k,v in counter:
    #     print(k,v)


# def replace_repeat_1_chars(match):
#     repeat_char=match.group(2)
#     # 获取匹配的字符串
#     chars = match.group(0)
#     # 返回替换文本，其中 {N} 是重复的字符数量
#     # return f'<MULTI-{len(chars)}-'+r'\2'+'-CHAR>'
#     return f'<|MULTI-{len(chars)}-{repeat_char}-CHAR|>'

# def replace_repeat_2_chars(match):
#     two_chars = match.group(2)  # 获取重复的两个字符
#     count = match.group(1).count(two_chars)  # 获取这两个字符重复的次数
#     return f'<MULTI-{count}-{two_chars}>'




    # @staticmethod
    # def find_consecutive_space_before_line_bracket(self,text):
    #     matches=re.finditer(DeDupSpan.pattern_space_1,text)
    #     for match in matches:
    #         print(match.group())
    # def find_consecutive_chars(self,text):
    #     consec_span_2_counter={}
    #     cur_consec_span=''
    #     bool_in_consec=False
    #     last_char=''
    #     for i in range(1,len(text)):
    #         if text[i]==last_char:
    #             bool_in_consec=True
    #             cur_consec_span+=text[i]
    #         else:
    #             last_char=text[i]
    #             bool_in_consec=False
    #             if cur_consec_span:
    #                 if consec_span_2_counter.get(cur_consec_span):
    #                     consec_span_2_counter[cur_consec_span]=0
    #                 consec_span_2_counter[cur_consec_span]+=1
    #         if i%100000==0:
    #             print(i)
    #     return consec_span_2_counter