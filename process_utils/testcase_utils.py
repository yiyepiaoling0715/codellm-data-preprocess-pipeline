from process_utils.dedup_content import FunctionPattern
from process_utils.lang_processor import LangJudge
from typing import Text,List,Dict
from process_utils.algo_utils import DependPathFounder
def judge_testcase_of_filename(filename):
    testcase_language_list,testcase_suffix_list=LangJudge.get_testcase_languages_and_suffix_list_tuple()
    if '/' in filename:
        filename=filename.split('/')[-1]
        suffix=filename.split('.')[-1]
        if suffix not in testcase_suffix_list:
            return False
    if 'test' in filename.lower():
        return True
    return False

def judge_testcase_of_filepath(filepath,src_dirpath_list):
    filepath_iter=filepath
    for src_dirpath_iter in src_dirpath_list:
        filepath_iter=filepath_iter.replace(src_dirpath_iter,'')
        # print(f'src_dirpath_list={src_dirpath_list},\nfilepath={filepath},\nfilepath_iter={filepath_iter}')
    if 'test' in filepath_iter.lower():
        return True
    return False

# def judge_testcase_of_func_text(fun_text):
def judge_testcase_of_func_signature(fun_text):
    
    # if 'test' in fun_text.lower():
    # searcher=FunctionPattern.suffix_num_pattern_for_func_text.search(fun_text)
    # if searcher:
    #     return True
    if FunctionPattern.prefix_test_pattern.search(fun_text):
        return True
    if FunctionPattern.suffix_text_num_pattern.search(fun_text):
        return True
    # if 'test' in fun_text:
    #     print(fun_text)
    return False

def get_func_info_by_func_signature(func_signature_iter:Text,path_iter:Text,project_root:Text,language:Text,
                                    filepath_2_func_info_dict:Dict,func_text_2_filepath_list_dict:Dict,):
    """
        通过函数签名和被引用锁在的路径,找到具体的实现函数的具体信息
    """                            
    filepath_list_iter=func_text_2_filepath_list_dict[func_signature_iter]
    if len(filepath_list_iter)>1:
        ##todo imports 引入
        most_match_path=DependPathFounder.pick_most_match_path(imports=[],import_src_filepath=path_iter,
                paths=filepath_list_iter,project_root=project_root,language=language)
    else:
        most_match_path=filepath_list_iter[0]
    func_info_iter=filepath_2_func_info_dict[most_match_path]['parent_2_function_definition_dict'][func_signature_iter]
    parent_2_sub_include_func_text_dict=filepath_2_func_info_dict[most_match_path]['parent_2_sub_include_func_text_dict'][func_signature_iter]
    
    depend_info_dict_iter={'filepath':most_match_path,
                           'func_signature_2_info_dict':{func_signature_iter:func_info_iter},
                           'parent_2_sub_include_func_text_dict':{func_signature_iter:parent_2_sub_include_func_text_dict}
                           }
    return depend_info_dict_iter


def get_tested_func_signature_by_test_signature(testcase_func_signature:Text,func_text_2_filepath_list_dict:Dict):
    """
        desc: 将 testcase 函数签名前后分别
    """
    func_text=testcase_func_signature
    func_text1=FunctionPattern.suffix_text_num_pattern.sub('',func_text)    
    func_text2=FunctionPattern.prefix_test_pattern.sub('',func_text1)    
    if len(func_text2)==len(testcase_func_signature):
        return False,func_text
    if func_text2 not in func_text_2_filepath_list_dict.keys():
        # if parent_func_text_iter in print_func_signature_list:
        #     print(f'enter in counter_tested_func_signature_in_func_text_2_filepath_list_dict_is_false,tested_func_signature_iter={tested_func_signature_iter}')
        # print(f'tested_func_signature_iter不在signature2path内,parent_func_text_iter={parent_func_text_iter},tested_func_signature_iter={tested_func_signature_iter}')
        Counter.counter_tested_func_signature_in_func_text_2_filepath_list_dict_is_false+=1
        return False,func_text
    return True,func_text2

def get_tested_func_signature_by_test_description(testcase_func_signature:Text,sub_include_func_text_iter:Text,
            func_text_2_filepath_list_dict:Dict,filepath_2_func_info_dict:Dict,path_iter:Text,project_root:Text,language:Text):
    """
        desc: 通过函数具体内容,获取函数内部调用的具体函数
    """
    depend_info_dict_list=[]
    sub_include_text_list=sub_include_func_text_iter.split(';')    
    for sub_include_text_iter in sub_include_text_list:
            if sub_include_text_iter not in func_text_2_filepath_list_dict.keys():
                continue
            depend_info_dict_iter=get_func_info_by_func_signature(filepath_2_func_info_dict=filepath_2_func_info_dict,
                                                                 func_text_2_filepath_list_dict=func_text_2_filepath_list_dict,
                                                                 func_signature_iter=sub_include_text_iter,
                                                                 path_iter=path_iter,
                                                                 project_root=project_root,
                                                                 language=language)
            depend_info_dict_list.append(depend_info_dict_iter)
    if len(depend_info_dict_list)==0:
        return False,depend_info_dict_list
    return True,depend_info_dict_list

def judge_testcase_by_func_description(func_signature:Text,sub_include_func_text:Text):
    """
        根据函数体内容,判断是否测试用例
    """
    ##todo 添加判断条件
    if 'assert' in sub_include_func_text.lower():
        return True
    return False
