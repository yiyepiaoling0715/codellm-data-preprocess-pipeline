import os
import sys
import codecs
import json
import numpy as np
import pandas as pd
import jsonlines
import pickle
import socket
import time
import numpy as np
from tree_sitter import Node,Tree
from typing import Text,List,Dict
from typing import Dict,List

# from repo_graphs.multi_dedup_file import progress_record_lang_2_file_2_imported_files_dict
from process_utils.path_utils import get_projects_dirpath_list
from process_utils.testcase_utils import (
        judge_testcase_by_func_description,
        # trans_testcase_func_signature_2_src_func_signature,
        get_tested_func_signature_by_test_description
        )
from process_utils.constants import Constants,FileterCounter,PROJECT_ROOT_DIRPATH,OUTPUT_DIRPATH,PaConstants
from process_utils.dedup_content import FunctionPattern
from repo_graphs.argparse_of_graph import get_argparse
from process_utils.common_utils import pprint_args
from process_utils.algo_utils import DependPathFounder
from process_utils.testcase_utils import judge_testcase_of_filepath
from repo_graphs.fim_parse import traverse_tree,PaserCodeFile
import lpai
import re
from concurrent.futures import ProcessPoolExecutor as ConcPool
import multiprocessing
import datasets
import pickle as pk
from datasets import load_dataset,Features,Value,ClassLabel,Dataset
from process_utils.utils import timeit
from process_utils.lang_processor import LangJudge

print_func_signature_list=['TestCase_OS_vMpSetStackRegion_001']

part_samples_of_part_tested_func_paths=['System/Bsw/CanIf/src/CanIf.c','System/Bsw/Com/src/Com_Com.c',
            'System/Bsw/SoAd/src/SoAd.c','System/Bsw/Det/src/Det.c','System/Os/AutosarOS/src/Os_Application.c']
part_samples_of_part_testcase_paths=['Test/CUnit/Testcase/Com_CUnit/canif',
                'Test/CUnit/Testcase/Com_CUnit/com','Test/CUnit/Testcase/OS_CUnit/Application']
check_filepath=[
        'xxx'
        ]

class Counter:
    #所有解析的函数数量
    counter_file_inall=0
    counter_testcase_file_after_filter_1_num_inall=0
    counter_parse_funcs_num_inall=0
    counter_judge_testcase_of_func_text_is_false=0
    counter_trans_testcase_func_signature_2_src_func_signature_is_false=0
    counter_tested_func_signature_in_func_text_2_filepath_list_dict_is_false=0
    counter_successful_sample=0

    @staticmethod
    def print():
        print_string=f'所有文件数量={Counter.counter_file_inall}\n' +\
            f'1次过滤后测试文件数量={Counter.counter_testcase_file_after_filter_1_num_inall}\n'+\
            f'所有的待解析的函数数量={Counter.counter_parse_funcs_num_inall}\n'+ \
            f'函数非测试用例形式数量={Counter.counter_judge_testcase_of_func_text_is_false},\n'+ \
            f'测试用例不能找到测试原函数signature数量={Counter.counter_trans_testcase_func_signature_2_src_func_signature_is_false}\n'+ \
            f'测试用例signature不在函数2文件路径映射数量={Counter.counter_tested_func_signature_in_func_text_2_filepath_list_dict_is_false}\n' +\
            f'最后成功保留的样本数量={Counter.counter_successful_sample}'
        print(print_string)

def get_parent_node_function_declarator_of_cpp(node,sub_all_check_node_list):
    bool_parent_key_exist=False
    parent_node_function_declarator=''
    for index_sub_node,sub_node in enumerate(sub_all_check_node_list):
        if (not bool_parent_key_exist) and sub_node.grammar_name=='function_declarator' and node.grammar_name=='function_definition':
            parent_node_function_declarator=sub_node.text
            bool_parent_key_exist=True        
            # print(f'父节点={node}, 子节点sub_node.text={sub_node.text},sub_node.grammar_name={sub_node.grammar_name},parent_node_function_declarator={parent_node_function_declarator}')        
            #移除的是用的节点
            sub_all_check_node_list.remove(sub_node)
            # try:
            #     assert parent_node_function_declarator not in parent_2_sub_include_func_text_dict.keys()
            # except AssertionError as e:
            #     # print(e.args)
            #     # print(f'parent_node_function_declarator出现过了={parent_node_function_declarator}')
            #     error_info1=f'父节点={node}, 子节点sub_node={sub_node},parent_node_function_declarator={parent_node_function_declarator}\n'
            #     error_info2=f'AssertionError,language={language},filepath={filepath}\n'
            #     error_info3=f'parent_node_function_declarator出现过了={parent_node_function_declarator}'
            #     print(error_info2+error_info3+error_info1)
            #     FileterCounter.funcname_same_in_onefile+=1
            #     # raise ValueError(error_info2+error_info3+error_info1)
            # parent_2_sub_include_func_text_dict[parent_node_function_declarator]=[]
            # # print(f'parent_node_function_declarator={parent_node_function_declarator}')
            if 'crypto_processjob_012' in codecs.decode(parent_node_function_declarator, 'utf-8'):
                print(f'check crypto_processjob_012 =\n {parent_node_function_declarator}')
            break
    return bool_parent_key_exist,parent_node_function_declarator

def get_parent_node_function_declarator_of_python(node,sub_all_check_node_list):
    """
        找到python的父节点
    """
    parent_node_1st_line=node.text.split(b'\n')[0]
    bool_parent_key_exist=False
    parent_node_function_declarator=''
    for index_sub_node,sub_node in enumerate(sub_all_check_node_list):
        # print(f'node={node},sub_node={sub_node},sub_node.text={sub_node.text}')
        if (not bool_parent_key_exist) and node.grammar_name=='function_definition' and sub_node.grammar_name=='identifier':
            if  sub_node.text not in ['def'] and sub_node.text in parent_node_1st_line:
                parent_node_function_declarator=sub_node.text
                if sub_node.text.startswith(b'_'):
                    return False,sub_node.text
                bool_parent_key_exist=True
                # print('python get_parent_node_function_declarator_of_python bool_parent_key_exist=true')
                break
    return bool_parent_key_exist,parent_node_function_declarator

def get_parent_node_function_declarator_proxy(language,node,sub_all_check_node_list):
    """
        代理器:找到所有语言父节点
    """
    if language==Constants.LANG_CPP:
        bool_parent_key_exist,parent_node_function_declarator=get_parent_node_function_declarator_of_cpp(node=node,sub_all_check_node_list=sub_all_check_node_list)
    elif language==Constants.LANG_PYTHON:
        bool_parent_key_exist,parent_node_function_declarator=get_parent_node_function_declarator_of_python(node=node,sub_all_check_node_list=sub_all_check_node_list)
    else:
        # raise Value(f'error 暂不支持 lang={language}')
        bool_parent_key_exist=False
        parent_node_function_declarator=''
    return bool_parent_key_exist,parent_node_function_declarator

@timeit
def parser_testcase_function_per_process(args_tuple):
    """
        从filepath,解析出 {父函数:子函数}, 父函数的body信息等
    """
    # print(f'parser_testcase_function_per_process args_tuple={args_tuple}')
    filepath,language,sub_process_index,process_index=args_tuple[0],args_tuple[1],args_tuple[2],args_tuple[3]
    parser=PaserCodeFile.lang_parse_proxy.get_parser(lang=language)
    if not parser:
        if np.random.random()<0.001:
            print(f'{language} no parser')
        return {}
    with open(filepath, 'rb') as file:
        source_bytes = file.read()
    time_0=time.time()
    tree = parser.parse(source_bytes)
    parent_2_function_definition_dict={}
    parent_2_sub_include_func_text_dict:Dict[Text,List]={}
    #for check
    check_sub_include_grammar_name_seen={}
    ##todo 过滤，找出有效的
    all_check_node_list:List[Node]=[node for node in traverse_tree(tree)]
    # print(f'all_check_node_list num={len(all_check_node_list)}')
    time_1=time.time()
    for node in all_check_node_list:
        # print(f'check parent node={node},grammar_name={node.grammar_name},sub_node.text[:100]={node.text[:100]}')    
        # if node.text in print_func_signature_list:
        #     print(f'check parent node={node},grammar_name={node.grammar_name},sub_node.text[:100]={node.text[:100]}')    
        # # if 'hsm_end_time' in codecs.decode(node.text,'utf-8'):
        # #     print(f'check parent node={node},grammar_name={node.grammar_name},sub_node.text[:100]={node.text[:100]}')    
        #grammar_name排除父节点
        if node.grammar_name in Constants.parent_func_class_exclude:            
            continue
        #过滤字符串node
        if node.grammar_name in ['string_literal'] and len(node.text)<50:
            continue
        #此处找父节点函数，func_defination, 函数一般长度都比较长,包括具体实现
        if len(node.text)<10:
            continue
        if node.end_point[0]-node.start_point[0]<2:
            continue
        #排除简单的父节点
        if len(node.grammar_name)<3:
            continue

        #此处找父节点函数，func_defination, 函数一般长度都比较长,包括具体实现
        if len(node.text)>10000:
            continue
        
        sub_all_check_node_list:List[Node]=[node for node in traverse_tree(node)]
        sub_all_check_node_list=sorted(sub_all_check_node_list,key=lambda x:x.start_byte,reverse=False)
        bool_parent_key_exist,parent_node_function_declarator=get_parent_node_function_declarator_proxy(language,node,sub_all_check_node_list)
        
        if bool_parent_key_exist:
            try:
                #前面被后面的覆盖
                assert parent_node_function_declarator not in parent_2_sub_include_func_text_dict.keys()
            except AssertionError as e:
                FileterCounter.funcname_same_in_onefile+=1
                # print(e.args)
                # print(f'parent_node_function_declarator出现过了={parent_node_function_declarator}')
                error_info1=f'父节点={node}, 子节点sub_node={sub_node},parent_node_function_declarator={parent_node_function_declarator}\n'
                error_info2=f'AssertionError,language={language},filepath={filepath}\n'
                error_info3=f'parent_node_function_declarator出现过了={parent_node_function_declarator}\n*************'
                if np.random.random()<0.001:
                    print(error_info2+error_info3 +error_info1)
                
            parent_2_sub_include_func_text_dict[parent_node_function_declarator]=[]
            parent_2_function_definition_dict[parent_node_function_declarator]=node.text
            # if language in [Constants.LANG_PYTHON]:
            #     print(f'parent_2_function_definition_dict[parent_node_function_declarator][:50]={parent_2_function_definition_dict[parent_node_function_declarator][:50]}')            
            for index_sub_node,sub_node in enumerate(sub_all_check_node_list):
                #根据子节点text长度过滤子节点
                if len(sub_node.text)<5:
                    continue
                #根据子节点类型过滤
                if sub_node.grammar_name in Constants.sub_func_class_exclude:
                    continue
                #for check begin
                # print(f'sub_node.text={sub_node.text},sub_node.grammar_name={sub_node.grammar_name},parent_node_function_declarator={parent_node_function_declarator}')
                # function_declarator_from_children_by_field_name=sub_node.children_by_field_name('function_declarator')
                # print(f'function_declarator_from_children_by_field_name={function_declarator_from_children_by_field_name}')
                # if sub_node.grammar_name in sub_grammer_names_include:
                #     continue
                # if sub_node.grammar_name not in check_sub_include_grammar_name_seen.keys():
                #     check_sub_include_grammar_name_seen[sub_node.grammar_name]=0
                # check_sub_include_grammar_name_seen[sub_node.grammar_name]+=1
                # if check_sub_include_grammar_name_seen[sub_node.grammar_name]>3:
                #     continue
                #for check end                
                # if b'TestCase_CAN_CanIf_017_002' in node.text[:50]:
                #     print(f'\tcheck 有效的sub_node.grammar_name sub_node={sub_node},\n grammar_name={sub_node.grammar_name},type={sub_node.type},\nsub_node.text[:100]={sub_node.text[:500]}')
                # print('---------------------')
                try:
                    # if sub_node.text not in parent_2_sub_include_grammar_names_dict[node.text]:
                    if sub_node.text not in parent_2_sub_include_func_text_dict[parent_node_function_declarator]:
                        if sub_node.text==parent_node_function_declarator:
                            continue
                        parent_2_sub_include_func_text_dict[parent_node_function_declarator].append(sub_node.text)
                        # print(f'sub_node.text={sub_node.text},sub_node.grammar_name={sub_node.grammar_name},parent_node_function_declarator={parent_node_function_declarator}')
                except UnboundLocalError as e:
                    print(f'UnboundLocalError for node={node},grammar_name={node.grammar_name},node.text[:100]={node.text[:100]}')                
                    raise ValueError('error')
        else:
            # print(f'bool_parent_key_exist={bool_parent_key_exist},parent_node_function_declarator={parent_node_function_declarator}')
            # return {}
            pass
    time_2=time.time()
    parent_2_sub_include_func_text_dict_encode={}
    for parent_text,sub_include_names_iter in parent_2_sub_include_func_text_dict.items():
        parent_text_encode=codecs.decode(parent_text,'utf-8')
        sub_include_names_iter_encode=[codecs.decode(sub_include_name,'utf-8') for sub_include_name in sub_include_names_iter]
        parent_2_sub_include_func_text_dict_encode[parent_text_encode]=sub_include_names_iter_encode
    time_3=time.time()

    #清洗 子节点signature,
    parent_2_sub_include_func_text_dict_cleaned:Dict[Text,List[Text]]={}
    for parent_text,sub_include_names in parent_2_sub_include_func_text_dict_encode.items():
        parent_text_cleaned=FunctionPattern.clean_node_text(node_text=parent_text)
        sub_include_name_cleaned_list_iter=set()
        for sub_include_name_iter in sub_include_names:
            sub_include_name_cleaned_iter=FunctionPattern.clean_node_text(node_text=sub_include_name_iter)
            sub_include_name_cleaned_list_iter.add(sub_include_name_cleaned_iter)
        if parent_text_cleaned in sub_include_name_cleaned_list_iter:
            sub_include_name_cleaned_list_iter.remove(parent_text_cleaned)    
        sub_include_name_cleaned_list_iter=[sub_include_name for sub_include_name in sub_include_name_cleaned_list_iter if sub_include_name]        
        parent_2_sub_include_func_text_dict_cleaned[parent_text_cleaned]=sub_include_name_cleaned_list_iter
    time_4=time.time()
    #for check
    if 'CUnit/Testcase/Infra_CUnit/Crypto/ARUIX_TC389/src/crypto_test_function.c' in filepath:
        must_have_parent_func_list=['crypto_aes_ecb_decrypt','crypto_aes_cbc_encrypt','str2bn','crypto_sha256_test',
            'Crypto_UsrCallOut_Erase','crypto_keyerase_test','hsm_ecc_sign_verify_test',
            'crypto_processjob_012'
            ]
        for must_have_parent_func_iter in must_have_parent_func_list:
            assert must_have_parent_func_iter in parent_2_sub_include_func_text_dict_cleaned.keys(),f'{must_have_parent_func_iter} not in parent_2_sub_include_func_text_dict_cleaned'
    if filepath in check_filepath:
        print(f'filepath={filepath},\nparent_2_sub_include_func_text_dict_encode={parent_2_sub_include_func_text_dict_encode},\n parent_2_function_definition_dict={len(parent_2_function_definition_dict)}')
    parent_2_function_definition_dict_of_encode={}
    for parent_text,function_definition in parent_2_function_definition_dict.items():
        parent_text_encode_with_bracket=codecs.decode(parent_text,'utf-8',errors='strict')
        #正则去除括号
        parent_text_encode=FunctionPattern.clean_node_text(node_text=parent_text_encode_with_bracket)
        function_definition_encode=codecs.decode(function_definition,'utf-8',errors='strict')
        
        parent_2_function_definition_dict_of_encode[parent_text_encode]=(parent_text_encode_with_bracket,function_definition_encode,parent_text_encode)
    time_5=time.time()
    # #for check begin
    for k,v in parent_2_sub_include_func_text_dict_cleaned.items():
        # parent_2_sub_include_grammar_names_dict_cleaned[k]=list(v)
        cleaned_v=FunctionPattern.batch_clean_node_text(node_text_list=v)
        parent_2_sub_include_func_text_dict_cleaned[k]=';'.join(cleaned_v)
    source_text=codecs.decode(source_bytes,'utf-8',errors='strict')
    if LangJudge.get_language_of_file(filepath) and  filepath.split('.')[-1] in LangJudge.get_language_of_file(filepath) in [Constants.LANG_PYTHON] and source_text.count('def ')>5:
        try:
            assert len(parent_2_function_definition_dict_of_encode)>0
        except AssertionError as e:
            err_msg=f'def num>5,parent_2_function_definition_dict_of_encode num=0,\n filepath={filepath}'
            raise ValueError(err_msg)
    time_6=time.time()
    if max(time_1-time_0,time_2-time_1,time_3-time_2,time_4-time_3,time_5-time_4,time_6-time_5)>5:
        print(f'process_index={process_index},sub_process_index={sub_process_index},traverse_tree耗时={time_1-time_0},len(all_check_node_list)={len(all_check_node_list)},filepath={filepath}')
        print(f'process_index={process_index},sub_process_index={sub_process_index},all_check_node_list 耗时={time_2-time_1},len(all_check_node_list)={len(all_check_node_list)},filepath={filepath}')
        print(f'process_index={process_index},sub_process_index={sub_process_index},parent_2_sub_include_func_text_dict_encode 耗时={time_3-time_2},len(parent_2_sub_include_func_text_dict_encode)={len(parent_2_sub_include_func_text_dict_encode)}')
        print(f'process_index={process_index},sub_process_index={sub_process_index},parent_2_sub_include_func_text_dict_cleaned 耗时={time_4-time_3}')
        print(f'process_index={process_index},sub_process_index={sub_process_index},parent_2_function_definition_dict_of_encode 耗时={time_5-time_4},len(parent_2_function_definition_dict_of_encode)={len(parent_2_function_definition_dict_of_encode)}')
        print(f'process_index={process_index},sub_process_index={sub_process_index},assert python def  耗时={time_6-time_5}')
    return {
        'parent_2_function_definition_dict':parent_2_function_definition_dict_of_encode,
        'parent_2_sub_include_func_text_dict':parent_2_sub_include_func_text_dict_cleaned,        

        'filepath':filepath,
        'language':language
    }
    

# 外部Pool任务
def inner_multi_process_function_info(language_list,filepath_list,index_process_list):
    """
        文件级别的处理,对每个文件进行tree_sitter解析,解析出function_info信息
    """
    # 在这里，我们将创建一个嵌套的Pool来运行更多的任务
    # print(f'Starting outer task with argument: {x}')
    # with multiprocessing.Pool(processes=multiprocessing.cpu_count()//2) as inner_pool:
    process_num=int(os.environ['process_num'])
    max_workers=min(process_num,max(len(filepath_list),1))
    print(f'inner_multi_process_function_info max_workers={max_workers},len(filepath_list)={len(filepath_list)}')
    # with ConcPool(max_workers=multiprocessing.cpu_count()//2) as inner_pool:
    if len(filepath_list)>200:
        with ConcPool(max_workers=max_workers) as inner_pool:
            # 使用 map 函数为了保证结果的顺序，而不是 apply_async
            sub_process_index_list=list(range(len(filepath_list)))
            chunksize=len(filepath_list)//max_workers
            try:
                sub_processes_generator = inner_pool.map(parser_testcase_function_per_process, list(zip(filepath_list,language_list,sub_process_index_list,index_process_list)),chunksize=chunksize)
                # sub_processes_generator = inner_pool.map(parser_testcase_function_per_process, list(zip(filepath_list,language_list,sub_process_index_list,index_process_list)))
            except TimeoutError as e:
                print('error timeout',e.args)
            new_function_info_list=[sub_processes_iter for sub_processes_iter in sub_processes_generator]
            new_function_info_list=[function_info for function_info in new_function_info_list if function_info]
    else:
        new_function_info_list=[]
        sub_process_index_list=list(range(len(filepath_list)))
        for filepath,language,sub_process_index,process_index in zip(filepath_list,language_list,sub_process_index_list,index_process_list):
            function_info_iter=parser_testcase_function_per_process(args_tuple=[filepath,language,sub_process_index,process_index])
            if function_info_iter:
                new_function_info_list.append(function_info_iter)
    return new_function_info_list

def filter_all_testcase_function_info(before_dedup_dirpath:Text,filepath_2_function_info_dict_jsonpath:Text,
                function_2_filepath_list_dict_jsonpath:Text,filepath_2_filepath_list_dict_jsonpath:Text,
                testcase_dataset_jsonpath:Text,src_dirpath_list:List[Text]):
    """
        multi_dedup_file.py处理完后,过滤出 testcase,并进行后续处理
    """
    # filepath_2_function_info_dict_jsonpath=os.path.join(OUTPUT_DIRPATH,'tmp_filepath_2_function_info_dict.json')
    # function_2_filepath_list_dict_jsonpath=os.path.join(OUTPUT_DIRPATH,'tmp_function_2_filepath_list_dict.json')
    with open(filepath_2_function_info_dict_jsonpath,'r') as fr:
        filepath_2_func_info_dict=json.load(fr)
    with open(function_2_filepath_list_dict_jsonpath,'r') as fr:
        func_text_2_filepath_list_dict=json.load(fr)
    with open(filepath_2_filepath_list_dict_jsonpath,'r') as fr:
        project_root_2_lang_2_filepath_2_filepath_list_dict=json.load(fr)
        DependPathFounder.init_static_variable(project_root_2_lang_2_filepath_2_filepath_list_dict=project_root_2_lang_2_filepath_2_filepath_list_dict)
    # testcase_dataset_jsonpath=os.path.join(OUTPUT_DIRPATH,'testcase_dataset.json')    

    dataset=before_dedup_dirpath
    split='train'
    print(f'before_dedup_dirpath={before_dedup_dirpath}')
    # datasets.config.fields=['language','project_path','function_name','function_definition','function_definition_encode','parent_2_function_definition_dict','parent_2_sub_include_grammar_names_dict']
    df = datasets.load_dataset(
        # path='json',
        path='parquet',
        # path='json',
        # data_dir=dataset,
        data_dir=dataset,
        # config,
        # data_dir=data_dir,
        split=split,
        num_proc=os.cpu_count(),
        keep_in_memory=True,
        cache_dir=None,
        features=PaConstants.features,
    )
    # df_from_pd=pd.read_json(dataset)
    # df=Dataset.from_pandas(df_from_pd)
    Counter.counter_file_inall=len(df)
    content_column=df['content']
    parent_2_function_definition_dict_column=df['parent_2_function_definition_dict']
    parent_2_sub_include_func_text_dict_column=df['parent_2_sub_include_func_text_dict']
    path_column=df['path']
    project_path_column=df['project_path']
    
    df_testcase=df.filter(lambda x:judge_testcase_of_filepath(x['path'],src_dirpath_list=src_dirpath_list)==True)
    # df_testcase=df
    Counter.counter_testcase_file_after_filter_1_num_inall=len(df_testcase)

    parent_2_function_definition_dict_column_of_testcase=df_testcase['parent_2_function_definition_dict']
    parent_2_sub_include_func_text_dict_column_of_testcase=df_testcase['parent_2_sub_include_func_text_dict']
    path_column=df_testcase['path'] 
    project_path_column=df_testcase['project_path'] 
    language_column=df_testcase['language'] 
    print(f'过滤testcase前数量len(df)={len(df)}')
    print(f'过滤testcase后数量len(df_testcase)={len(df_testcase)}')
    print(f'parent_2_function_definition_dict_column_of_testcase数量={len(parent_2_function_definition_dict_column_of_testcase)}')
    testcase_dataset_json_list=[]
    for index,parent_2_function_definition_dict_text_iter in enumerate(parent_2_function_definition_dict_column_of_testcase):
        parent_2_sub_include_func_text_dict_iter=parent_2_sub_include_func_text_dict_column_of_testcase[index]
        parent_2_sub_include_func_text_dict_iter=json.loads(parent_2_sub_include_func_text_dict_iter)
        parent_2_function_definition_dict_text_iter=json.loads(parent_2_function_definition_dict_text_iter)
        path_iter=path_column[index]
        project_path_iter=project_path_column[index]
        language_iter=language_column[index]
        #check begin
        for print_func_signature_iter in print_func_signature_list:
            if print_func_signature_iter in parent_2_function_definition_dict_text_iter.keys():
                print('---------check print test func begin-------------------')
                print(f'print_func_signature_iter={print_func_signature_iter}')
                print(parent_2_function_definition_dict_text_iter[print_func_signature_iter])
                print(parent_2_sub_include_func_text_dict_iter[print_func_signature_iter])
                print('---------check print test func end-------------------')
        #check end
        depend_func_info_list=[]
        for parent_func_text_iter,sub_include_func_text_iter in parent_2_sub_include_func_text_dict_iter.items():
            Counter.counter_parse_funcs_num_inall+=1
            #check begin
            if parent_func_text_iter in print_func_signature_list:
                print(f'check print_func_signature_list,parent_func_text_iter={parent_func_text_iter}')
                # print(judge_testcase_of_func_text(fun_text=parent_func_text_iter))
                # print(trans_testcase_func_signature_2_src_func_signature(testcase_func_signature=parent_func_text_iter))
                print(parent_func_text_iter in func_text_2_filepath_list_dict[project_path_iter][language_iter].keys())
                print('-------------------------------')
            #check end
            # #根据是否能从 prefix=testxxx, suffix=__01维度解析出来
            if not judge_testcase_by_func_description(func_signature=parent_func_text_iter,
                                          sub_include_func_text=sub_include_func_text_iter):
                # if 'test' in parent_func_text_iter or '001' in parent_func_text_iter:
                #     print(f'未从testcase_signature解析出原signature,parent_func_text_iter={parent_func_text_iter}')
                if parent_func_text_iter in print_func_signature_list:
                    print('enter in counter_judge_testcase_of_func_text_is_false')
                Counter.counter_judge_testcase_of_func_text_is_false+=1
                continue
            
            bool_testcase,depend_info_dict_list=get_tested_func_signature_by_test_description(
                    ##todo  del args in  testcase_func_signature
                    testcase_func_signature=parent_func_text_iter,
                    sub_include_func_text_iter=sub_include_func_text_iter,
                    path_iter=path_iter,
                    func_text_2_filepath_list_dict=func_text_2_filepath_list_dict[project_path_iter][language_iter],
                    filepath_2_func_info_dict=filepath_2_func_info_dict[project_path_iter][language_iter],
                    project_root=project_path_iter,language=language_iter)
            if not bool_testcase:
                print(f'未从sub_include_func_text_iter解析出被测试的signature,parent_func_text_iter={parent_func_text_iter},\n'+\
                      f'sub_include_func_text_iter={sub_include_func_text_iter}')
                if parent_func_text_iter in print_func_signature_list:
                    print('enter in counter_trans_testcase_func_signature_2_src_func_signature_is_false')
                Counter.counter_trans_testcase_func_signature_2_src_func_signature_is_false+=1
                continue
            ##todo 改为list
            #获取被测函数的具体信息,tested_filepath_iter、tested_func_signature_iter、tested_sub_include_func_text_iter
            tested_func_info_iter=depend_info_dict_list[0]
            tested_filepath_iter=tested_func_info_iter['filepath']
            tested_func_signature_iter=list(tested_func_info_iter['func_signature_2_info_dict'].keys())[0]
            tested_sub_include_func_text_iter=tested_func_info_iter['parent_2_sub_include_func_text_dict'][tested_func_signature_iter]
            # tested_parent_2_sub_include_func_text_dict_iter=filepath_2_func_info_dict[project_path_iter][language_iter][tested_filepath_iter]['parent_2_sub_include_func_text_dict']
            # tested_sub_include_func_text_iter=filepath_2_func_info_dict[project_path_iter][language_iter][tested_filepath_iter]['parent_2_sub_include_func_text_dict'][tested_func_signature_iter]
            bool_testcase,depend_info_dict_list_of_tested_signature_iter=get_tested_func_signature_by_test_description(
                    ##todo  del args in  testcase_func_signature
                    testcase_func_signature=tested_func_signature_iter,
                    sub_include_func_text_iter=tested_sub_include_func_text_iter,
                    path_iter=tested_filepath_iter,
                    func_text_2_filepath_list_dict=func_text_2_filepath_list_dict[project_path_iter][language_iter],
                    filepath_2_func_info_dict=filepath_2_func_info_dict[project_path_iter][language_iter],
                    project_root=project_path_iter,language=language_iter)
            # func_text_2_filepath_list_dict:Dict,filepath_2_func_info_dict:Dict,path_iter:Text,project_root:Text,language:Text
            # tested_filepath=depend_info_dict_list[0]['filepath']
            # tested_func_signature_2_info_dict=depend_info_dict_list[0]['func_signature_2_info_dict']
            
            if parent_func_text_iter in print_func_signature_list:
                print(f'after get_func_info_by_func_signature tested_func_info_iter={tested_func_info_iter}')
            center_func_info_dict_iter=filepath_2_func_info_dict[project_path_iter][language_iter][path_iter]['parent_2_function_definition_dict'][parent_func_text_iter]

            testcase_info_dict_iter={
                                     'tested_func_info':tested_func_info_iter,
                                     'testcase_depend_info_dict_list':depend_info_dict_list_of_tested_signature_iter,
                                     'testcase_center_path':path_iter,
                                     'testcase_center_func_info_dict':center_func_info_dict_iter,
                                     }
            testcase_dataset_json_list.append(testcase_info_dict_iter)
            if parent_func_text_iter in print_func_signature_list:
                print(f'check print_func_signature_list,parent_func_text_iter={parent_func_text_iter}')
                print(f'testcase_info_dict_iter={testcase_info_dict_iter}')
            Counter.counter_successful_sample+=1

    with jsonlines.open(testcase_dataset_jsonpath,'w') as fw:
        for line in testcase_dataset_json_list:
            fw.write(line)    
    part_sample_list=[]
    for testcase_json_iter in  testcase_dataset_json_list:
        tested_func_filepath_iter=testcase_json_iter['tested_func_info']['filepath']
        testcase_filepath_iter=testcase_json_iter['testcase_center_path']
        bool_tested_path_match=False
        for path_iter in part_samples_of_part_tested_func_paths:
            if path_iter in tested_func_filepath_iter:
                bool_tested_path_match=True
                break
        if not bool_tested_path_match:
            continue
        bool_testcase_path_match=False
        for path_iter in part_samples_of_part_testcase_paths:
            if path_iter in testcase_filepath_iter:
                bool_testcase_path_match=True
                break
        if not bool_testcase_path_match:
            continue
        part_sample_list.append(testcase_json_iter)
        
    part_testcase_dataset_jsonpath=testcase_dataset_jsonpath.replace('.json','_part.json')
    with jsonlines.open(part_testcase_dataset_jsonpath,'w') as fw:
        for line in part_sample_list:
            fw.write(line)    

    print(f'测试用例写入路径=\n{testcase_dataset_jsonpath}')
    Counter.print()

if __name__=='__main__':
    args=get_argparse()
    pprint_args(args=args)  
    before_dedup_dirpath=args.before_dedup_dirpath

    if socket.gethostbyname(socket.gethostname())=='192.168.4.60':
        before_dedup_dirpath="xxx"
        filepath_2_function_info_dict_jsonpath=os.path.join(OUTPUT_DIRPATH,'filepath_2_function_info_dict.json')
        function_2_filepath_list_dict_jsonpath=os.path.join(OUTPUT_DIRPATH,'function_2_filepath_list_dict.json')
        filepath_2_filepath_list_dict_jsonpath=os.path.join(OUTPUT_DIRPATH,'filepath_2_filepath_list_dict.json')
        testcase_dataset_jsonpath=os.path.join(OUTPUT_DIRPATH,'testcase_dataset.json')
        src_dirpath_list=['xxx']
    else:
        before_dedup_dirpath=args.before_dedup_dirpath
        filepath_2_function_info_dict_jsonpath=args.filepath_2_function_info_dict_jsonpath
        function_2_filepath_list_dict_jsonpath=args.function_2_filepath_list_dict_jsonpath
        filepath_2_filepath_list_dict_jsonpath=args.filepath_2_filepath_list_dict_jsonpath
        testcase_dataset_jsonpath=args.testcase_dataset_jsonpath
        src_dirpath_list=args.src_dirpath_list.split(',')
        
    filter_all_testcase_function_info(before_dedup_dirpath=before_dedup_dirpath,
        filepath_2_function_info_dict_jsonpath=filepath_2_function_info_dict_jsonpath,
        function_2_filepath_list_dict_jsonpath=function_2_filepath_list_dict_jsonpath,
        filepath_2_filepath_list_dict_jsonpath=filepath_2_filepath_list_dict_jsonpath,
        testcase_dataset_jsonpath=testcase_dataset_jsonpath,
        src_dirpath_list=src_dirpath_list
        )




