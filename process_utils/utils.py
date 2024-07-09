import time
import os
import numpy as np
from functools import wraps
from typing import List,Dict,Text
from process_utils.constants import Constants


def time_decorator_with_prompt(prompt_infor):
    def time_decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            print(prompt_infor + ", Time =", time.time() - start_time)
            return result
        return decorated
    return time_decorator

def timeit(func):
    """ Decorate a function to print its arguments.
    """
    @wraps(func)
    def my_func(*args, **kwargs):
        start_time = time.time()
        res=func(*args, **kwargs)
        end_time = time.time()
        ts=end_time-start_time
        if ts>300:
            print("执行函数：{}，函数运行时间为：{} s".format(func.__name__, ts))
        return res

    return my_func

def remove_personal_path_prefix(filepath,src_dirpath_list=None):
    """
        filepath 删除前面的环境相关的无效路径
    """
    if src_dirpath_list is None:
        src_dirpath_list=os.environ['src_dirpath_list'].split(',')
    else:
        assert isinstance(src_dirpath_list,list)
        
    new_filepath=filepath
    bool_replace=False
    for path_frefix_iter in src_dirpath_list:
        if filepath.startswith(path_frefix_iter):
            new_filepath=new_filepath.replace(path_frefix_iter,'')
            bool_replace=True
    assert bool_replace==True,print(f"src_dirpath_list={os.environ['src_dirpath_list']},\nfilepath={filepath}")
    return new_filepath

def concat_filepath(filepath):
    ##?? todo 为何+ \n
    # writed_filepath=f'{Constants.FILEPATH_START_TOKEN}\n{Constants.FILEPATH_FLAG}:'+filepath+f'\n{Constants.FILEPATH_END_TOKEN}'
    writed_filepath=f'{Constants.FILEPATH_START_TOKEN}\t{Constants.FILEPATH_FLAG}:'+filepath+f'{Constants.FILEPATH_END_TOKEN}'+'\n'
    return writed_filepath
    
def concat_path_and_content(filepath,content):
    filepath_del_prefix=remove_personal_path_prefix(filepath=filepath)
    writed_filepath=concat_filepath(filepath=filepath_del_prefix)
    new_content=writed_filepath+content
    return new_content


def read_content_with_ignore_error(filepath):
    try:
        # with open(filepath, 'r',encoding='utf-8',errors='ignore') as fr:
        with open(filepath, 'r',encoding='utf-8',errors='strict') as fr:
            try:
                content=fr.read()
            except UnicodeDecodeError as e:
                if np.random.random()<0.01:
                    print(f'UnicodeDecodeError when read file_path={filepath}')
                    print('error head 100=',str(e.args)[:100],'error tail 100=',str(e.args)[-100:])
                return None
    except UnicodeDecodeError as e:
        if np.random.random()<0.01:            
            print(f'UnicodeDecodeError when open file_path={self.filepath}')
            print('error head 100=',str(e.args)[:100],'error tail 100=',str(e.args)[-100:])
        return None

    return content

def merge_dict_list_of_same_key(dict_list:List[Dict[Text,List]]):
    merged_dict=dict_list[0]
    for dict_iter in dict_list[1:]:
        for k,v in dict_iter.items():
            if k not in merged_dict.keys():
                merged_dict[k]=v
            else:
                merged_dict[k]+=v
    for dict_iter in dict_list:
        assert len(merged_dict)>=len(dict_iter)
        for check_k,check_v in dict_iter.items():
            assert len(merged_dict[check_k])>=len(check_v)
    merged_dict={k:list(set(v)) for k,v in merged_dict.items()}
    return merged_dict


def merge_dict_dep_2_list_of_same_key(dict_list:List[Dict[Text,Dict[Text,List]]],project_root,language):
    all_paths_for_check_1=[]
    for dict_iter in dict_list:
        for k,v in dict_iter.items():
            for k1,v1 in v.items():
                if isinstance(v1,str):
                    v1=[v1]
                all_paths_for_check_1+=v1

    merged_dict=dict_list[0]
    for k,v in merged_dict.items():
        for k1,v1 in v.items():
            if isinstance(v1,str):
                v1=[v1]
            merged_dict[k][k1]=v1
                
    for dict_iter in dict_list[1:]:
        for k,v in dict_iter.items():
            if k not in merged_dict.keys():
                merged_dict[k]={}
                for k1,v1 in v.items():
                    if isinstance(v1,str):
                        v1=[v1]
                    merged_dict[k][k1]=v1
                # merged_dict[k]=v
            else:
                for k1,v1 in v.items():
                    # if k1 not in merged_dict[k].keys():
                    try:
                        assert k1 not in merged_dict[k].keys()
                    except AssertionError as e:
                        error_msg=f'k={k},k1={k1},v1={v1},\nmerged_dict[k]={merged_dict[k]}'
                        # raise ValueError(error_msg)
                    # merged_dict[k][k1]=list(set(v1))
                    if isinstance(dict_iter[k][k1],str):
                        dict_iter[k][k1]=[dict_iter[k][k1]]
                    if isinstance(v1,str):
                        v1=[v1]
                    merged_dict[k][k1]=list(set(dict_iter[k][k1]+v1))
                    # else:
                    #     assert
                        # merged_dict[k][k1]+=v1
    for dict_iter in dict_list:
        assert len(merged_dict)>=len(dict_iter)
        for check_k,check_v in dict_iter.items():
            assert len(merged_dict[check_k])>=len(check_v)
    
    all_paths_for_check_2=[]
    for check_k,check_v in merged_dict.items():
        for check_k1,check_v1 in check_v.items():
            assert isinstance(check_v1,list)
            all_paths_for_check_2+=check_v1
    # merged_dict={k:list(set(v)) for k,v in merged_dict.items()}
    try:
        assert len(all_paths_for_check_1)==len(all_paths_for_check_2)
    except AssertionError as e:
        print(f'merge_dict_dep_2_list_of_same_key 文件数量不一致 project_root={project_root},language={language},len(all_paths_for_check_1)={len(all_paths_for_check_1)},len(all_paths_for_check_2)={len(all_paths_for_check_2)}')
    return merged_dict


