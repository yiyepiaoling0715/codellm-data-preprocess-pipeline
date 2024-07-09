import os
import socket
import json
import shutil
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import collections
import time
from typing import Dict,List,Tuple
from process_utils.utils import timeit,read_content_with_ignore_error
from process_utils.lang_processor import LangJudge
from process_utils.constants import PathTemplate,Constants,FileterCounter,PaConstants
from process_utils.path_utils import get_group_repos_mark,get_filepath_2_depend_filepath_list_dict_after_cpp_compile
from repo_graphs.argparse_of_graph import get_argparse
from process_utils.common_utils import pprint_args
from process_utils.path_utils import get_projects_dirpath_list
# from process_utils.testcase_utils import judge_testcase_of_filename,judge_testcase_of_func_text
from process_utils.testcase_utils import judge_testcase_of_filename
from concurrent.futures import ProcessPoolExecutor as ConcPool
from repo_graphs.reconstruct import ParseManager
from testcase.main_process import inner_multi_process_function_info
import multiprocessing
from process_utils.constants import PROJECT_ROOT_DIRPATH
import timeout_decorator

# @timeit
@timeout_decorator.timeout(60*30)
def progress_record_lang_2_file_2_imported_files_dict(param_args):
    """
        仓库级别的处理,仓库内所有的语言均处理
        按照文件维度记录各个维度的有效信息
    """
    index_process,args,project_root,write_dirpath,project_name,department=param_args[0],param_args[1],param_args[2],param_args[3],param_args[4],param_args[5]
    time_start=time.time()
    print(f'开始的进程index_process={index_process},project_root={project_root},project_name={project_name}')
    language_list_of_project=LangJudge.get_allowed_language_list_of_project(project_root=project_root)
    lang_2_filepath_2_imported_files_dict=ParseManager.create_repo_import_dict_of_language_list(language_list=language_list_of_project,project_root=project_root)
    time_1=time.time()
    print(f'进程index_process={index_process},under create_repo_import_dict_of_language_list lang_2_filepath_2_imported_files_dict num={len(lang_2_filepath_2_imported_files_dict)},time_cost={time_1-time_start}')
    ##todo 文件级多进程添加函数级解析
    sample_list_of_repo=[]
    for lang_iter,filepath_2_imported_files_dict_iter in lang_2_filepath_2_imported_files_dict.items():
        for filepath_iter,imported_files_iter in filepath_2_imported_files_dict_iter.items():
            bool_testcase=judge_testcase_of_filename(filename=filepath_iter)
            # print(f'file_iter={file_iter}')
            content=read_content_with_ignore_error(filepath=filepath_iter)
            if not content:
                continue
            sample_dict_iter={
                'language':lang_iter,
                'project_path':project_root,
                'path':filepath_iter,
                # 'imported_files':';'.join(imported_files_iter),
                'imported_files':json.dumps(imported_files_iter,ensure_ascii=False),
                'src_encoding':'utf-8',
                'repo_name':project_name,
                'github_id':department,
                'content':content,
                'bool_testcase':bool_testcase
            }
            sample_list_of_repo.append(sample_dict_iter)

    if not sample_list_of_repo:
        print(f'进程index_process={index_process},没有内容可以写入文件 project_root={project_root},project_name={project_name},department={department}')
        return None,index_process,None,None,None,None,project_root
    time_2=time.time()
    print(f'进程index_process={index_process},每个进程内部,sample_list_of_repo数量={len(sample_list_of_repo)},time_cost={time_2-time_1}')

    #每个文件解析内部函数信息
    language_list=[sample_dict_iter['language'] for sample_dict_iter in sample_list_of_repo]
    filepath_list=[sample_dict_iter['path'] for sample_dict_iter in sample_list_of_repo]
    function_info_list=inner_multi_process_function_info(language_list=language_list,filepath_list=filepath_list,index_process_list=[index_process]*len(filepath_list))
    filepath_2_function_info_dict={function_info_iter['filepath']:function_info_iter for function_info_iter in function_info_list}
    time_3=time.time()
    print(f'进程index_process={index_process},under inner_multi_process_function_info 每个进程内部,sample_list_of_repo数量={len(sample_list_of_repo)},time_cost={time_3-time_2}')
    #将依据tree_sitter解析的function_info_list 添加到sample_list_of_repo中
    for index_sample,sample_dict_iter in enumerate(sample_list_of_repo):
        filepath_iter=sample_dict_iter['path']
        # try:
        #     assert filepath_iter in filepath_2_function_info_dict.keys()
        # except AssertionError as e:
        #     # print(f'filepath_iter={filepath_iter}')
        #     raise ValueError(f'AssertionError filepath_iter={filepath_iter}')
        # assert filepath_2_function_info_dict[filepath_iter]['language']==sample_dict_iter['language']
        if filepath_iter in filepath_2_function_info_dict.keys() and filepath_2_function_info_dict[filepath_iter]['parent_2_function_definition_dict']:
            assert filepath_2_function_info_dict[filepath_iter]['language']==sample_dict_iter['language']
            update_dict_iter={
                'parent_2_function_definition_dict':filepath_2_function_info_dict[filepath_iter]['parent_2_function_definition_dict'],
                'parent_2_sub_include_func_text_dict':filepath_2_function_info_dict[filepath_iter]['parent_2_sub_include_func_text_dict'],
            }
            FileterCounter.has_filepath_2_function_counter+=1
            assert len(filepath_2_function_info_dict[filepath_iter]['parent_2_function_definition_dict'])>0
            if np.random.random()<0.001:
                print(f'进程index_process={index_process},正确解析出parent_2_function_definition_dict,filepath_iter={filepath_iter},language={sample_dict_iter["language"]},update_dict_iter={update_dict_iter},index_sample={index_sample}')
        
        else:
            if filepath_iter in filepath_2_function_info_dict.keys():
                assert len(filepath_2_function_info_dict[filepath_iter]['parent_2_function_definition_dict'])==0
            update_dict_iter={
                'parent_2_function_definition_dict':{},
                'parent_2_sub_include_func_text_dict':{},
            }
            if sample_dict_iter['language'] in [Constants.LANG_CPP,Constants.LANG_PYTHON] and np.random.random()<0.001:
                print(f'进程index_process={index_process},没有解析出parent_2_function_definition_dict,filepath_iter={filepath_iter},language={sample_dict_iter["language"]},len(sample_dict_iter)={len(sample_dict_iter)},index_sample={index_sample}')
            FileterCounter.no_filepath_2_function_counter+=1
        sample_dict_iter.update(update_dict_iter)
    time_4=time.time()
    print(f'进程index_process={index_process} under sample_list_of_repo 更新parent_2_function_definition_dict,time_cost={time_4-time_3}')

    # ##tmp for check
    # filepath_2_function_info_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/tmp_filepath_2_function_info_dict.json')
    # with open(filepath_2_function_info_dict_jsonpath,'w') as fw:
    #     json.dump(filepath_2_function_info_dict,fw,ensure_ascii=False,indent=4)    
    # function_2_filepath_list_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/tmp_function_2_filepath_list_dict.json')
    # with open(function_2_filepath_list_dict_jsonpath,'w') as fw:
    #     json.dump(function_2_filepath_list_dict,fw,ensure_ascii=False,indent=4)    

    # filepath_2_sample_list_of_repo_dict={sample_dict_iter['path']:sample_dict_iter for sample_dict_iter in sample_list_of_repo}
    # for function_info_iter in function_info_list:        
    #     filepath_iter=function_info_iter['filepath']
    #     assert filepath_iter in filepath_2_sample_list_of_repo_dict.keys()
    #     assert filepath_2_sample_list_of_repo_dict[filepath_iter]['language']==function_info_iter['language']
    #     update_dict_iter={
    #         'parent_2_function_definition_dict':function_info_iter['parent_2_function_definition_dict'],
    #         'parent_2_sub_include_grammar_names_dict':function_info_iter['parent_2_sub_include_grammar_names_dict'],
    #     }
    #     filepath_2_sample_list_of_repo_dict[filepath_iter].update(update_dict_iter)

    before_dedup_dirpath=PathTemplate.before_dedup_dirpath.format(write_dirpath=write_dirpath)
    # shutil.rmtree(before_dedup_dirpath,ignore_errors=True)
    # os.makedirs(before_dedup_dirpath,exist_ok=True)
    parse_path_dict=get_group_repos_mark(project_root=project_root,last_n=3)
    last_n_dir_str=parse_path_dict['last_n_dir_str']
    write_jsonpath=os.path.join(before_dedup_dirpath,f'{last_n_dir_str}.json')
    assert not os.path.exists(write_jsonpath)
    #有dump begin
    # with open(write_jsonpath, 'w', encoding='utf-8') as fw:
    #     for info_json_iter in sample_list_of_repo:
    #         try:
    #             assert len(info_json_iter.keys())==11
    #             info_json_str=json.dumps(info_json_iter,ensure_ascii=False)+'\n'
    #         except TypeError as e:               
    #             error_info=''
    #             for check_k,check_v in info_json_iter.items():                    
    #                 error_info_iter=f'check_k={check_k},check_v={check_v}\n'
    #                 error_info+=error_info_iter
    #             print(f'TypeError info_json_iter={error_info}\n')                
    #             raise e
    #         fw.write(info_json_str)
    #有dump end
    # #无dump begin
    # with jsonlines.open(write_jsonpath, 'w') as fw:
    #     for info_json_iter in sample_list_of_repo:
    #         try:
    #             assert len(info_json_iter.keys())==11
    #             # info_json_str=json.dumps(info_json_iter,ensure_ascii=False)+'\n'
    #             info_json_str=info_json_iter
    #         except TypeError as e:               
    #             error_info=''
    #             for check_k,check_v in info_json_iter.items():                    
    #                 error_info_iter=f'check_k={check_k},check_v={check_v}\n'
    #                 error_info+=error_info_iter
    #             print(f'TypeError info_json_iter={error_info}\n')                
    #             raise e
    #         fw.write(info_json_str)
    # #无dump end
    # #std json format begin
    sample_list_of_repo_of_jsonformat={}
    for info_json_iter in sample_list_of_repo:
        for k,v in info_json_iter.items():
            if k not in sample_list_of_repo_of_jsonformat.keys():
                sample_list_of_repo_of_jsonformat[k]=[]
            if isinstance(v,dict):
                v=json.dumps(v,ensure_ascii=False)
            sample_list_of_repo_of_jsonformat[k].append(v)
    # with open(write_jsonpath, 'w', encoding='utf-8') as fw:
    #     json.dump(sample_list_of_repo_of_jsonformat,fw,ensure_ascii=False,indent=4)
    # #std json format end
    time_5=time.time()
    print(f'进程index_process={index_process},on pyarow,time_cost={time_5-time_4}')
    try:
        batch_list=[]
        batch_size=int(np.ceil(len(sample_list_of_repo_of_jsonformat['language'])/10000))
        for batch_index in range(batch_size):
            # batch = pa.StructArray.from_arrays(
            batch_iter = pa.RecordBatch.from_arrays(
                [
                    pa.array(sample_list_of_repo_of_jsonformat['language'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['project_path'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['path'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['imported_files'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['src_encoding'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['repo_name'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['github_id'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['content'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['bool_testcase'][batch_index*10000:(batch_index+1)*10000],type=pa.bool_()),
                    pa.array(sample_list_of_repo_of_jsonformat['parent_2_function_definition_dict'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    pa.array(sample_list_of_repo_of_jsonformat['parent_2_sub_include_func_text_dict'][batch_index*10000:(batch_index+1)*10000],type=pa.string()),
                    # pa.array(sample_list_of_repo_of_jsonformat['parent_2_function_definition_dict'],type=pa.dictionary()),
                    # pa.array(sample_list_of_repo_of_jsonformat['parent_2_sub_include_grammar_names_dict'],type=pa.dictionary()),
                ],
                names=PaConstants.dedup_schema.names,        
            )
            batch_list.append(batch_iter)
    except TypeError as e:
        print('进程index_process={index_process},pyarrow batch 长度=',len(sample_list_of_repo_of_jsonformat['language']))
        raise ValueError(f"TypeError  pyarrow batch 长度={len(sample_list_of_repo_of_jsonformat['language'])}")
    # table = pa.Table.from_batches([batch])
    table = pa.Table.from_batches(batch_list)
    # table=pa.Table.from_arrays(batch,names=dedup_schema.names)
    pq.write_table(table, write_jsonpath)
    time_6=time.time()
    print(f'进程index_process={index_process},under pyarow,time_cost={time_6-time_5}')

    #利用function_info_list 实现 function_2_filepath_list_dict
    # function_2_filepath_list_dict={}
    language_2_function_2_filepath_list_dict={}
    for function_info_iter in function_info_list:
        filepath_iter=function_info_iter['filepath']
        lang_iter=function_info_iter['language']
        if lang_iter not in language_2_function_2_filepath_list_dict.keys():
            language_2_function_2_filepath_list_dict[lang_iter]={}
        parent_2_sub_include_func_text_dict=function_info_iter['parent_2_sub_include_func_text_dict']
        for parent_func_text_iter,parent_2_sub_include_func_text_iter in parent_2_sub_include_func_text_dict.items():
            # if parent_func_text_iter not in function_2_filepath_list_dict.keys():
            if parent_func_text_iter not in language_2_function_2_filepath_list_dict[lang_iter].keys():
                # function_2_filepath_list_dict[parent_func_text_iter]=[filepath_iter]
                language_2_function_2_filepath_list_dict[lang_iter][parent_func_text_iter]=[filepath_iter]
            else:
                # function_2_filepath_list_dict[parent_func_text_iter].append(filepath_iter)
                language_2_function_2_filepath_list_dict[lang_iter][parent_func_text_iter].append(filepath_iter)

    language_2_filepath_2_function_info_dict={}
    for filepath_iter,function_info_iter in filepath_2_function_info_dict.items():
        lang_iter=function_info_iter['language']
        if lang_iter not in language_2_filepath_2_function_info_dict.keys():
            language_2_filepath_2_function_info_dict[lang_iter]={}
        language_2_filepath_2_function_info_dict[lang_iter][filepath_iter]=function_info_iter
    project_root_2_language_2_filepath_2_function_info_dict={project_root:language_2_filepath_2_function_info_dict}
    project_root_2_language_2_function_2_filepath_list_dict={project_root:language_2_function_2_filepath_list_dict}
    time_7=time.time()
    print(f'结束的进程index_process={index_process},project_root={project_root},project_name={project_name},time_cost={time_7-time_6}')
    # return write_jsonpath,index_process,sample_list_of_repo,FileterCounter.counter_info(),filepath_2_function_info_dict,function_2_filepath_list_dict
    return write_jsonpath,index_process,sample_list_of_repo,FileterCounter.counter_info(),project_root_2_language_2_filepath_2_function_info_dict,project_root_2_language_2_function_2_filepath_list_dict,project_root

def multi_process_repos(src_dirpath_list,write_dirpath,root_dir_of_cpp_compile_abspath,
                        args,process_num):
    """
        针对仓库级别的多进程处理，每个进程处理一个仓库的数据
    """
    before_dedup_dirpath=PathTemplate.before_dedup_dirpath.format(write_dirpath=write_dirpath)
    shutil.rmtree(before_dedup_dirpath,ignore_errors=True)
    os.makedirs(before_dedup_dirpath,exist_ok=True)

    fileter_counter_dict_inall={'has_filepath_2_function_counter':0,
                                'no_filepath_2_function_counter':0}
    # write_jsonpath_inall_all_process=[]
    sample_list_of_repo_all_process=[]
    # filepath_2_function_info_dict_inall={}
    # function_2_filepath_list_dict_inall={}
    project_root_2_language_2_filepath_2_function_info_dict_inall={}
    project_root_2_language_2_function_2_filepath_list_dict_inall={}
    #[(repo_dir,write_dir),...]
    src_dst_path_tuple_list=get_projects_dirpath_list(src_dirpath_list,write_dirpath)
    print(f'进程数process_num={process_num},总处理project数量len(src_dst_path_tuple_list)={len(src_dst_path_tuple_list)}')
    # with multiprocessing.Pool(processes=process_num) as pool:
    # from concurrent.futures import ProcessPoolExecutor as ConcPool
    with ConcPool(max_workers=process_num) as pool:
        args_list=[[index_process,args,*src_dst_path_tuple_iter] for index_process,src_dst_path_tuple_iter in enumerate(src_dst_path_tuple_list)]
        stack_group_num_range_2_counter_inall={}
        # print(f'总计需要处理的进程数量={len(args_list)}')
        assert len(args_list)==len(src_dst_path_tuple_list)
        # for res_iter in pool.imap_unordered(process_project,args_list):
        for res_iter in pool.map(progress_record_lang_2_file_2_imported_files_dict,args_list):
            write_jsonpath_per_process=res_iter[0]
            sample_list_of_repo=res_iter[2]
            fileter_counter_dict_iter:Dict=res_iter[3]
            project_root_2_language_2_filepath_2_function_info_dict_iter=res_iter[4]
            project_root_2_language_2_function_2_filepath_list_dict_iter=res_iter[5]
            project_root=res_iter[6]
            if not sample_list_of_repo:
                print(f'仓库内没有样本解析出来,project_root={project_root}')
                continue
            sample_list_of_repo_all_process.extend(sample_list_of_repo)
            assert project_root not in project_root_2_language_2_filepath_2_function_info_dict_inall.keys()
            project_root_2_language_2_filepath_2_function_info_dict_inall.update(project_root_2_language_2_filepath_2_function_info_dict_iter)
            assert project_root not in project_root_2_language_2_function_2_filepath_list_dict_inall.keys()
            project_root_2_language_2_function_2_filepath_list_dict_inall.update(project_root_2_language_2_function_2_filepath_list_dict_iter)
            # for check_filepath_iter in filepath_2_function_info_dict_iter.keys():
            #     assert check_filepath_iter not in filepath_2_function_info_dict_inall.keys()
            # filepath_2_function_info_dict_inall.update(filepath_2_function_info_dict_iter)
            # for function_iter,filepath_list_iter in function_2_filepath_list_dict_iter.items():
            #     if function_iter not in function_2_filepath_list_dict_inall.keys():
            #         function_2_filepath_list_dict_inall[function_iter]=filepath_list_iter
            #     else:
            #         function_2_filepath_list_dict_inall[function_iter].extend(filepath_list_iter)
            # function_2_filepath_list_dict_inall.update(function_2_filepath_list_dict_iter)
            print(f'index_process={res_iter[1]} 执行完毕退出,写入路径={write_jsonpath_per_process}')
            fileter_counter_dict_inall['has_filepath_2_function_counter']+=fileter_counter_dict_iter['has_filepath_2_function_counter']
            fileter_counter_dict_inall['no_filepath_2_function_counter']+=fileter_counter_dict_iter['no_filepath_2_function_counter']
    
    project_root_2_filepath_2_filepath_list_dict_inall={}
    for root_dir_iter in root_dir_of_cpp_compile_abspath:
        filepath_2_filepath_list_dict_iter=get_filepath_2_depend_filepath_list_dict_after_cpp_compile(root_dir=root_dir_iter)
        project_root_2_filepath_2_filepath_list_dict_iter={root_dir_iter:{Constants.LANG_CPP:filepath_2_filepath_list_dict_iter}}
        project_root_2_filepath_2_filepath_list_dict_inall.update(project_root_2_filepath_2_filepath_list_dict_iter)
    ##todo 添加assert 判断filepath2filepath 正确


    # ##tmp for check
    # filepath_2_function_info_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/tmp_filepath_2_function_info_dict.json')
    # with open(filepath_2_function_info_dict_jsonpath,'w') as fw:
    #     json.dump(filepath_2_function_info_dict,fw,ensure_ascii=False,indent=4)    
    # function_2_filepath_list_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/tmp_function_2_filepath_list_dict.json')
    # with open(function_2_filepath_list_dict_jsonpath,'w') as fw:
    #     json.dump(function_2_filepath_list_dict,fw,ensure_ascii=False,indent=4) 
    # filepath_2_function_info_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/tmp_filepath_2_function_info_dict.json')
    with open(args.filepath_2_function_info_dict_jsonpath,'w') as fw:
        json.dump(project_root_2_language_2_filepath_2_function_info_dict_inall,fw,ensure_ascii=False,indent=4)    
    # function_2_filepath_list_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/tmp_function_2_filepath_list_dict.json')
    with open(args.function_2_filepath_list_dict_jsonpath,'w') as fw:
        json.dump(project_root_2_language_2_function_2_filepath_list_dict_inall,fw,ensure_ascii=False,indent=4) 
    with open(args.filepath_2_filepath_list_dict_jsonpath,'w') as fw:
        json.dump(project_root_2_filepath_2_filepath_list_dict_inall,fw,ensure_ascii=False,indent=4) 
    print(f'文件和文件的映射关系写入路径={args.filepath_2_filepath_list_dict_jsonpath},写入仓库数量={len(project_root_2_filepath_2_filepath_list_dict_inall.keys())}')
    for check_k,check_v in project_root_2_filepath_2_filepath_list_dict_inall.items():
        for check_k1,check_v1 in check_v.items():
            print(f'文件和文件的映射关系 project_root_2_filepath_2_filepath_list_dict_inall 读取的仓库路径={check_k},写入语言={check_k1},\n 写入文件数量={len(check_v1)}')
    print(f'所有进程执行完毕,总写入路径数量{len(sample_list_of_repo_all_process)}')
    langs_inall=[sample_iter['language'] for sample_iter in sample_list_of_repo_all_process]
    lang_2_counter_dict=collections.Counter(langs_inall).most_common(50)
    print(f'解析的的top50语言={lang_2_counter_dict}')
            # write_jsonpath_inall_all_process.extend(write_jsonpath_inall_per_process)
        # sample_list_of_repo,write_jsonpath=progress_record_lang_2_file_2_imported_files_dict(param_args=param_args)
    print('*******过程数量统计FILETER_COUNTER_DICT_INALL********')
    for print_k,print_v in fileter_counter_dict_inall.items():        
        print(f'{print_k}={print_v}')
    return 

if __name__=='__main__':
    args=get_argparse()

    if socket.gethostbyname(socket.gethostname())=='xxx':

        process_num=10
        args.filepath_2_function_info_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/filepath_2_function_info_dict.json')
        args.function_2_filepath_list_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/function_2_filepath_list_dict.json')
        args.filepath_2_filepath_list_dict_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'output/filepath_2_filepath_list_dict.json')
    else:
        process_num=multiprocessing.cpu_count()
    pprint_args(args=args)    
    os.environ['process_num']=str(process_num)
    os.environ['src_dirpath_list']=args.src_dirpath_list
    src_dirpath_list=args.src_dirpath_list.split(',')
    root_dir_of_cpp_compile_abspath=args.root_dir_of_cpp_compile_abspath.split(',')
    # os.environ['src_dirpath_list']=args.src_dirpath_list
    multi_process_repos(src_dirpath_list=src_dirpath_list,
                        write_dirpath=args.write_dirpath,
                        args=args,process_num=process_num,
                        root_dir_of_cpp_compile_abspath=root_dir_of_cpp_compile_abspath)