import os
import shutil
import socket
import time
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor as ConcPool
from deprecated import deprecated
import sys
from typing import Dict,List,Tuple,Text
import collections
import numpy as np
sys.setrecursionlimit(2500)  # 将最大递归深度设置为1500

from process_utils.utils import timeit
from process_utils.common_utils import FIMProxy,pprint_args
from process_utils.lang_processor import LangJudge
from repo_graphs.reconstruct import ParseManager
from process_utils.constants import PathTemplate,FileterCounter
from process_utils.path_utils import (deal_repo_content_2_info_json,
    info_json_list_deal_of_group_by_file_max_size,
    get_group_repos_mark,
    get_projects_dirpath_list,
    write_department_info_by_list)

from repo_graphs.make_graph_of_dfs import make_graph_process_of_languages
from repo_graphs.fim_deal_in_node import concat_text_by_graph,process_pathnode_with_fim
from repo_graphs.attributes.calc_lens import calc_val_about_len_columns
from process_utils.dedup_content import DeDupSpan
# from concurrent.futures import ProcessPoolExecutor as Pool
from repo_graphs.fim_parse import PaserCodeFile
from repo_graphs.attributes.calc_lens import calc_feature_of_conent
from repo_graphs.argparse_of_graph import get_argparse
import datasets

def load_lang_2_file_2_imported_files_dict_from_dataset(dataset_path_after_dedup,write_dirpath)->List[Dict]:
    """
        处理为 {lang:file:import_filename:import_filepath} 的 级联映射形式
    """
    project_name_2_lang_2_file_2_imported_files_dict={}
    project_name_2_lang_2_file_2_project_path_dict={}
    ds=datasets.load_from_disk(dataset_path=dataset_path_after_dedup)    
   
    content=ds['content']
    for iterow in ds.iter(batch_size=1):
        language=iterow['language'][0]
        path=iterow['path'][0]
        imported_files_str=iterow['imported_files'][0]
        imported_name_2_path_dict=json.loads(imported_files_str)
        github_id=iterow['github_id'][0]
        project_name=iterow['repo_name'][0]
        project_path=iterow['project_path'][0]
        if project_name not in project_name_2_lang_2_file_2_imported_files_dict.keys():
            project_name_2_lang_2_file_2_imported_files_dict[project_name]={}
            project_name_2_lang_2_file_2_project_path_dict[project_name]={}
        if language not in project_name_2_lang_2_file_2_imported_files_dict[project_name].keys():
            project_name_2_lang_2_file_2_imported_files_dict[project_name][language]={}
            project_name_2_lang_2_file_2_project_path_dict[project_name][language]={}
        assert path not in project_name_2_lang_2_file_2_imported_files_dict[project_name][language].keys()
        project_name_2_lang_2_file_2_imported_files_dict[project_name][language][path]=imported_name_2_path_dict
        project_name_2_lang_2_file_2_project_path_dict[project_name][language]=project_path

    elem_dict_list=[]    
    idnex_process=0
    for project_name in project_name_2_lang_2_file_2_imported_files_dict.keys():
        for language in project_name_2_lang_2_file_2_imported_files_dict[project_name].keys():
            file_2_imported_files_dict=project_name_2_lang_2_file_2_imported_files_dict[project_name][language]
            project_path=project_name_2_lang_2_file_2_project_path_dict[project_name][language]
            elem_dict={
                "lang_2_file_2_imported_files_dict":{language:file_2_imported_files_dict},
                "project_path":project_path,
                "project_name":project_name,
                "department":github_id,
                "write_dirpath":write_dirpath,
                "index_process":idnex_process
            }
            elem_dict_list.append(elem_dict)
            idnex_process+=1
    print(f'用于多进程处理的lang_2_file_2_imported_files_dict_list数量(仓库&语言)={len(elem_dict_list)},仓库数量={len(project_name_2_lang_2_file_2_imported_files_dict)}')
    # project_path,write_dirpath_iter,project_name,department)
    return elem_dict_list

# def create_args_list_for_multi(dataset_path_after_dedup):
#     elem_dict_list=load_lang_2_file_2_imported_files_dict_from_dataset(dataset_path_after_dedup)
#     return elem_dict_list
@timeit
def inner_single_proc_deal_content(args_tuple:List)->Tuple[Text,Dict]:
    """
        切分为 content内容后,按照切分后的content 进行 正则清洗,统计
    """
    content,language,filepath=args_tuple[0],args_tuple[1],args_tuple[2]
    try:
        new_content=DeDupSpan.clean_text_by_re(text=content,filepath=filepath)
    except TypeError as e:
        raise ValueError(f'inner_single_proc_deal_content error content={content}')
    if args.bool_calc_feature:
        len_val_dict=calc_feature_of_conent(content=content,language=language)
    else:
        len_val_dict={}
    return (new_content,len_val_dict)

# 外部Pool任务
def inner_multi_process_content(content_list,language_list,filepath_list_after_graph):
    # 在这里，我们将创建一个嵌套的Pool来运行更多的任务
    # print(f'Starting outer task with argument: {x}')
    # with multiprocessing.Pool(processes=multiprocessing.cpu_count()//2) as inner_pool:
    max_workers=min(multiprocessing.cpu_count(),max(len(content_list)//20,1))
    # with ConcPool(max_workers=multiprocessing.cpu_count()//2) as inner_pool:
    with ConcPool(max_workers=max_workers) as inner_pool:
        # 使用 map 函数为了保证结果的顺序，而不是 apply_async
        sub_processes_generator = inner_pool.map(inner_single_proc_deal_content, list(zip(content_list,language_list,filepath_list_after_graph)))
        new_content_list=[sub_processes_iter for sub_processes_iter in sub_processes_generator]
    # print(f'Ending outer task with argument: {x}')
    return new_content_list

def process_node_num_eq_1_graph(stack_list_of_num_eq_1,filepaths_list_of_num_eq_1,language_list_of_num_eq_1):
    """
        对 拓扑图堆栈内 只有1个node的内容进行处理,
    """
    fim_string_list=[]
    fim_string_per_node_concate_list=[]
    language_list_num_eq_1=[]
    filepath_list_num_eq_1=[]
    stack_index_list_num_eq_1=[]
    index_stack=0
    for stack_list_iter,filepaths_list_iter,language_iter in zip(stack_list_of_num_eq_1,filepaths_list_of_num_eq_1,language_list_of_num_eq_1):
        try:
            assert len(stack_list_iter)==len(filepaths_list_iter)==1,print('Assert stack应该只有1个nodelength error=',len(stack_list_iter),len(filepaths_list_iter))
        except AssertionError as e:
            print('filepaths_list_iter=\n',language_iter,filepaths_list_iter)
            print('stack_list_iter=\n',stack_list_iter)

        # new_content_iter with #Path
        # print('process_node_num_eq_1_graph language_iter=',language_iter)
        # bool_content,new_content_iter=process_pathnode(node_iter=stack_list_iter[0])
        ## 为什么只处理第一个 stack_list_iter[0]=> eq_1 就只有1个
        bool_content,ret_content_dict=process_pathnode_with_fim(node=stack_list_iter[0],
                                                    source='single_file',bool_fim=True)
        if not bool_content:
            #process_pathnode_with_fim 已经统计过
            continue
        # fim_string_list_per_node=ret_content_dict['fim_string_list_per_node']
        fim_string_per_node_concat=ret_content_dict['new_content']
        ##todo 应该都为1
        filepath_iter=filepaths_list_iter
        
        fim_string_per_node_concate_list.append(fim_string_per_node_concat)
        # fim_string_list.extend(fim_string_list_per_node)

        language_list_num_eq_1.append(language_iter)
        filepath_list_num_eq_1.append(filepath_iter)
        stack_index_list_num_eq_1.append(index_stack)
        index_stack+=1
    return fim_string_list,fim_string_per_node_concate_list,language_list_num_eq_1,filepath_list_num_eq_1,stack_index_list_num_eq_1


@timeit
def process_project(param_args):
    # index_process,args,project_root,write_dirpath,project_name,department=param_args[0],param_args[1],param_args[2],param_args[3],param_args[4],param_args[5]
    # language_list_of_project=LangJudge.get_allowed_language_list_of_project(project_root=project_root)
    # #创建 {lang:file:import_list} 的映射关系
    # lang_2_file_2_imported_files_dict=ParseManager.create_repo_import_dict_of_language_list(language_list=language_list_of_project,project_root=project_root)
    lang_2_file_2_imported_files_dict=param_args['lang_2_file_2_imported_files_dict']
    project_path=param_args['project_path']
    project_name=param_args['project_name']
    department=param_args['department']
    write_dirpath=param_args['write_dirpath']
    index_process=param_args['index_process']
    
    ##所有允许的语言->stack_list均包括了
    #List[List[PathNode]],List[List[str]]
    stack_list_all,filepaths_list_all,language_list_all=make_graph_process_of_languages(lang_2_file_2_imported_files_dict=lang_2_file_2_imported_files_dict)
    assert len(stack_list_all)==len(filepaths_list_all)==len(language_list_all)
    stack_group_num_list=[len(stack_list_iter) for stack_list_iter in stack_list_all]
    stack_group_num_2_counter_dict=collections.Counter(stack_group_num_list)
    stack_group_num_range_2_counter={}
    for stack_group_num_iter,counter_iter in stack_group_num_2_counter_dict.items():
        if stack_group_num_iter<=10:
            area_num=stack_group_num_iter
        else:
            area_num=(np.ceil(stack_group_num_iter//100)+1)*100
        if area_num>5000:
            area_num=5000
        if area_num not in stack_group_num_range_2_counter.keys():
            stack_group_num_range_2_counter[area_num]=0
        stack_group_num_range_2_counter[area_num]+=counter_iter
    # check_stack_list_of_num_1=[check_stack_list_iter for check_stack_list_iter in stack_list_all if len(check_stack_list_iter)==1 ]
    # if check_stack_list_of_num_1:
    #     print('**************数量为1的filepath=**************')
    #     for stack_list_iter in check_stack_list_of_num_1:
    #             print(stack_list_iter[0].filepath)

    stack_list_of_num_eq_1,filepaths_list_of_num_eq_1,language_list_of_num_eq_1,stack_index_list_num_eq_1=[],[],[],[]
    stack_list_of_num_gt_1,filepaths_list_of_num_gt_1,language_list_of_num_gt_1,stack_index_list_num_gt_1=[],[],[],[]
    
    # for stack_list_iter,filepaths_list_iter,language_list_iter in zip(stack_list_all,filepaths_list_all,language_list_all):
    for stack_list_iter,filepaths_list_iter,language_iter in zip(stack_list_all,filepaths_list_all,language_list_all):
        if len(stack_list_iter)==1:
            stack_list_of_num_eq_1.append(stack_list_iter)
            filepaths_list_of_num_eq_1.append(filepaths_list_iter)
            language_list_of_num_eq_1.append(language_iter)
        else:
            stack_list_of_num_gt_1.append(stack_list_iter)
            filepaths_list_of_num_gt_1.append(filepaths_list_iter)
            language_list_of_num_gt_1.append(language_iter)
    assert len(stack_list_of_num_eq_1)+len(stack_list_of_num_gt_1)==len(stack_list_all)

    parse_path_dict=get_group_repos_mark(project_root=project_path,last_n=3)
    last_n_dir_str=parse_path_dict['last_n_dir_str']
    extra_path_str=parse_path_dict['extra_path_str']
    
    write_repo_json_dir=PathTemplate.write_repo_json_dir.format(write_dirpath=write_dirpath)
    write_repo_json_train_dir=PathTemplate.write_repo_json_train_dir.format(write_dirpath=write_dirpath)
    write_repo_file_map_dir=PathTemplate.write_repo_file_map_dir.format(write_dirpath=write_dirpath)
    sub_word_counter_dirpath=PathTemplate.sub_word_counter_dirpath.format(write_dirpath=write_dirpath)

    ts111=time.time()    
    _,fim_string_per_node_concate_list_num_eq_1,language_list_num_eq_1,filepath_list_num_eq_1,stack_index_list_num_eq_1=process_node_num_eq_1_graph(
                                stack_list_of_num_eq_1=stack_list_of_num_eq_1,
                                filepaths_list_of_num_eq_1=filepaths_list_of_num_eq_1,
                                language_list_of_num_eq_1=language_list_of_num_eq_1)
    assert len(fim_string_per_node_concate_list_num_eq_1)<=len(stack_list_of_num_eq_1)            
    
    if not stack_index_list_num_eq_1:
        # print(f'stack_index_list_num_eq_1 为空 fim_string_list={fim_string_list}')
        print(f'stack_index_list_num_eq_1 为空')
    # ts1=time.time()

    max_stack_index_list_num_eq_1=max(stack_index_list_num_eq_1) if stack_index_list_num_eq_1 else 0
    write_jsonpath_inall=[]
    # index_2_stack_content_dict={}
    content_list_num_gt_1=[]
    language_list_num_gt_1=[]
    filepaths_list_num_gt_1=[]
    stack_index_list_num_gt_1=[]
    ts112=time.time()
    # for index_stack,stack_iter in enumerate(stack_list_all):
    for index_stack,stack_iter in enumerate(stack_list_of_num_gt_1):
        language_iter=language_list_all[index_stack]
        filepaths_iter=filepaths_list_all[index_stack]
        # content_iter=concat_text_by_graph(stack=stack_iter,extra_dirpath_str=extra_path_str)
        #按照 GRAPH_CONTENT_MAX_SIZE切片后的, 50M
        content_list_per_stack=concat_text_by_graph(stack=stack_iter,extra_dirpath_str=extra_path_str)
        content_list_per_stack=[content_iter for content_iter in content_list_per_stack if content_iter]
        
        content_list_num_gt_1.extend(content_list_per_stack)
        language_list_num_gt_1.extend([language_iter]*len(content_list_per_stack))
        filepaths_list_num_gt_1.extend([filepaths_iter]*len(content_list_per_stack))
        stack_index_list_num_gt_1.extend([index_stack]*len(content_list_per_stack))
    ts113=time.time()

    stack_index_list_num_gt_1=[stack_index_iter+max_stack_index_list_num_eq_1 for stack_index_iter in stack_index_list_num_gt_1]
    
    raw_content_list_after_graph=fim_string_per_node_concate_list_num_eq_1+content_list_num_gt_1
    raw_language_list_after_graph=language_list_num_eq_1+language_list_num_gt_1
    raw_filepath_list_after_graph=filepath_list_num_eq_1+filepaths_list_num_gt_1
    raw_stack_index_list_after_graph=stack_index_list_num_eq_1+stack_index_list_num_gt_1

    content_list_after_graph,language_list_after_graph,filepath_list_after_graph,stack_index_list_after_graph=[],[],[],[]
    for index_content in range(len(raw_content_list_after_graph)):
        if not raw_content_list_after_graph[index_content]:
            continue
        content_list_after_graph.append(raw_content_list_after_graph[index_content])
        language_list_after_graph.append(raw_language_list_after_graph[index_content])
        filepath_list_after_graph.append(raw_filepath_list_after_graph[index_content])
        stack_index_list_after_graph.append(raw_stack_index_list_after_graph[index_content])

    # if len(content_list)<int(os.environ['INNER_MULTI_CONTENT_NUM_THRES']):
    if len(content_list_after_graph)<int(os.environ['INNER_MULTI_CONTENT_NUM_THRES']):
        new_content_list=[]
        for content_iter in content_list_after_graph:
            # if content_iter:
            new_content=DeDupSpan.clean_text_by_re(text=content_iter)
            new_content_list.append(new_content)
        len_val_dict_list=[]
        for index_content,content_iter in enumerate(new_content_list):
            if args.bool_calc_feature:
                print(filepath_list_after_graph[index_content])
                len_val_dict=calc_feature_of_conent(content=content_iter,language=language_iter)
            else:
                len_val_dict={}
            len_val_dict_list.append(len_val_dict)
    else:
        print(f'执行subprocess处理, content_list数量={len(content_list_after_graph)}')
        # inner_multiprocess_return_list=inner_multi_process_content(content_list=content_list,language_list=[language_iter]*len(content_list))
        inner_multiprocess_return_list=inner_multi_process_content(
                                    content_list=content_list_after_graph,
                                    language_list=language_list_after_graph,
                                    filepath_list_after_graph=filepath_list_after_graph)
        new_content_list=[elem[0] for elem in inner_multiprocess_return_list]
        len_val_dict_list=[elem[1] for elem in inner_multiprocess_return_list]
    ts114=time.time()
    # del content_list
    # del content_list_after_graph

    info_json_list=[]
    sample_truncate_serial_num_list=[]
    for check_content in content_list_after_graph:
        assert len(check_content)>10,print(f'len(check_content)={len(check_content)}')
    assert len(len_val_dict_list)==len(new_content_list),print(f'len(len_val_dict_list)={len(len_val_dict_list)},len(new_content_list)={len(new_content_list)}')
    for index_content,content_iter in enumerate(new_content_list):
        info_json_iter=deal_repo_content_2_info_json(
                    len_val_dict=len_val_dict_list[index_content],
                    content=content_iter,
                    project_name=project_name,
                    filepaths=filepath_list_after_graph[index_content],
                    language=language_list_after_graph[index_content],
                    sample_truncate_serial_num=(stack_index_list_after_graph[index_content],index_content))
        # print('flags=',(index_stack,index_content))
        info_json_list.append(info_json_iter)
        sample_truncate_serial_num_iter=info_json_iter['sample_truncate_serial_num']
        sample_truncate_serial_num_list.append(sample_truncate_serial_num_iter)
        # index_2_stack_content_dict[index_stack]=content_iter
    ts115=time.time()
    assert len(list(set(sample_truncate_serial_num_list)))==len(sample_truncate_serial_num_list)
    if info_json_list:
        ##todo last_2_dir/project_name 重复
        ##构建 {filepath:input_file_list}
        # unique_project_name=f'{last_2_dir}__{project_name}'
        unique_project_name=last_n_dir_str
        file_2_imported_files_jsonpath=os.path.join(write_repo_file_map_dir,f'file_2_imported_files_{unique_project_name}.json')
        with open(file_2_imported_files_jsonpath,'w') as fw:
            json.dump(lang_2_file_2_imported_files_dict,fw,indent=4)
        base_write_jsonpath=f'{write_repo_json_train_dir}/{unique_project_name}.json'
        #根据GRAPH_FILE_MAX_SIZE 切分 内容,是1整个文件内容作为elem的
        info_json_str_list=info_json_list_deal_of_group_by_file_max_size(info_json_list=info_json_list)

        for index_part,part_info_json_str_iter in enumerate(info_json_str_list):
            write_jsonpath_iter=base_write_jsonpath.replace('.json','_{:03}.json'.format(index_part))
            with open(write_jsonpath_iter,'w') as fw:
                for info_json_iter in part_info_json_str_iter:
                    fw.write(info_json_iter)    
            write_jsonpath_inall.append(write_jsonpath_iter)
        ts2=time.time()
        for filepath_iter in write_jsonpath_inall:
            DeDupSpan.find_char_and_words_from_jsonfile(filepath=filepath_iter,write_dirpath=sub_word_counter_dirpath,bool_clean=False)    
        ts3=time.time()
        if max(ts112-ts111,ts113-ts112,ts114-ts113,ts115-ts114,ts2-ts115,ts3-ts2)>300:
            for lang_iter,file_2_imported_files_dict_iter in lang_2_file_2_imported_files_dict.items():
                print(f'index_process={index_process},lang_iter={lang_iter},构建成功的引用关系数量={len(file_2_imported_files_dict_iter)}')
            # print(f'耗时:ts5-ts4={ts5-ts4},ts4-ts3={ts4-ts3},ts3-ts2={ts3-ts2},ts2-ts1={ts2-ts1},ts115-ts1={ts115-ts1}')
            print(f'耗时:ts3-ts2={ts3-ts2},ts112-ts111={ts112-ts111},ts113-ts112={ts113-ts112},ts114-ts113={ts114-ts113},ts115-ts114={ts115-ts114}')
            # print(f'index_process={index_process},for 循环 stack_list_all ts115-ts1={ts115-ts1}')
            print(f'index_process={index_process},write_dirpath={write_dirpath},len(stack_list_all)={len(stack_list_all)}')
            print(f'写入路径 base_write_jsonpath={base_write_jsonpath}')
            print(f'index_process={index_process},写入成功的文件数量={len(info_json_list)},写入耗时={ts3-ts2},project_name={project_name}')
            print(f'处理的write_jsonpath_inall文件数量={len(write_jsonpath_inall)}')
            DeDupSpan.print()
            # print(f'DeDupSpan.pat_rep_2_counter_dict={DeDupSpan.pat_rep_2_counter_dict}')
            # print(f'DeDupSpan.all_pat_rep_2_counter={DeDupSpan.all_pat_rep_2_counter}')
            print(f'执行写入路径write_dirpath={write_dirpath}')
            print(f'fim_string_per_node_concate_list_num_eq_1数量={len(fim_string_per_node_concate_list_num_eq_1)},content_list_num_gt_1数量={len(content_list_num_gt_1)}')
    return write_jsonpath_inall,index_process,stack_group_num_range_2_counter,FileterCounter.counter_info()

# def multi_process_repos(src_dirpath_list,write_dirpath,args,process_num):
def multi_process_repos(dataset_path_after_dedup,write_dirpath,args,process_num):
    #输入输出路径整理
    write_repo_json_dir=PathTemplate.write_repo_json_dir.format(write_dirpath=write_dirpath)
    write_repo_json_train_dir=PathTemplate.write_repo_json_train_dir.format(write_dirpath=write_dirpath)
    write_repo_file_map_dir=PathTemplate.write_repo_file_map_dir.format(write_dirpath=write_dirpath)
    sub_word_counter_dirpath=PathTemplate.sub_word_counter_dirpath.format(write_dirpath=write_dirpath)
    os.makedirs(write_repo_json_dir,exist_ok=True)
    os.makedirs(write_repo_json_train_dir,exist_ok=True)
    os.makedirs(write_repo_file_map_dir,exist_ok=True)
    os.makedirs(sub_word_counter_dirpath,exist_ok=True)
    #[(repo_dir,write_dir),...]
    # src_dst_path_tuple_list=get_projects_dirpath_list(src_dirpath_list,write_dirpath)
    # print(f'进程数process_num={process_num},总处理project数量len(src_dst_path_tuple_list)={len(src_dst_path_tuple_list)}')
    # with multiprocessing.Pool(processes=process_num) as pool:
    with ConcPool(max_workers=process_num) as pool:
        # args_list=[[index_process,args,*src_dst_path_tuple_iter] for index_process,src_dst_path_tuple_iter in enumerate(src_dst_path_tuple_list)]
        args_list=load_lang_2_file_2_imported_files_dict_from_dataset(dataset_path_after_dedup=dataset_path_after_dedup,write_dirpath=write_dirpath)
        language_set_inall=set([list(elem['lang_2_file_2_imported_files_dict'].keys())[0] for elem in args_list])
        department_list=list(set([elem['department'] for elem in args_list]))
        write_department_info_by_list(department_list=department_list,write_dirpath=write_dirpath)
        print(f'进程数process_num={process_num},总处理project数量len(args_list)={len(args_list)}')
        stack_group_num_range_2_counter_inall={}
        write_jsonpath_inall_all_process=[]
        fileter_counter_dict_inall={}
        grammar_name_2_counter_dict_inall={}
        # for res_iter in pool.imap_unordered(process_project,args_list):
        for res_iter in pool.map(process_project,args_list):
            print(f'index_process={res_iter[1]} 执行完毕退出')
            write_jsonpath_inall_per_process=res_iter[0]
            write_jsonpath_inall_all_process.extend(write_jsonpath_inall_per_process)
            stack_group_num_range_2_counter=res_iter[2]
            fileter_counter_dict=res_iter[3]
            for stack_group_num_range_iter,counter_iter in stack_group_num_range_2_counter.items():
                if stack_group_num_range_iter not in stack_group_num_range_2_counter_inall.keys():
                    stack_group_num_range_2_counter_inall[stack_group_num_range_iter]=0
                stack_group_num_range_2_counter_inall[stack_group_num_range_iter]+=counter_iter
            grammar_name_2_counter_dict_iter=fileter_counter_dict.pop('grammar_name_2_counter_dict')
            for filter_name,counter_iter in fileter_counter_dict.items():
                if filter_name not in fileter_counter_dict_inall.keys():
                    fileter_counter_dict_inall[filter_name]=0
                fileter_counter_dict_inall[filter_name]+=counter_iter
            for grammar_name_iter,counter_iter in grammar_name_2_counter_dict_iter.items():                
                if grammar_name_iter not in grammar_name_2_counter_dict_inall.keys():
                    grammar_name_2_counter_dict_inall[grammar_name_iter]=0
                grammar_name_2_counter_dict_inall[grammar_name_iter]+=counter_iter
        # results = [pool.apply_async(process_project,args=src_dst_path_tuple_iter) for src_dst_path_tuple_iter in src_dst_path_tuple_list]
        # results = [pool.apply(process_project,args=src_dst_path_tuple_iter) for src_dst_path_tuple_iter in src_dst_path_tuple_list]
        ##apply_async
        # results = [pool.apply_async(func=process_project,args=[*src_dst_path_tuple_iter,index_process]) for index_process,src_dst_path_tuple_iter in enumerate(src_dst_path_tuple_list)]
        # print(f"Using imap_unordered: process num={len(results)}")
        # for result_iter in results:
        #     print('多进程处理写入的文件路径为',result_iter.get())
    
    # word_counter_dirpath=f'{write_dirpath}/word_counter'
    # sub_word_counter_dirpath=f'{write_dirpath}/word_counter/sub_word_counter'
    # os.makedirs(sub_word_counter_dirpath,exist_ok=True)
    word_counter_dirpath=PathTemplate.word_counter_dirpath.format(write_dirpath=write_dirpath)
    sub_word_counter_dirpath=PathTemplate.sub_word_counter_dirpath.format(write_dirpath=write_dirpath)

    ts1=time.time()
    char_and_span_counter_jsonpath=os.path.join(word_counter_dirpath,'char_and_span_counter.json')
    DeDupSpan.merge_sub_word_counter_files(src_dirpath=sub_word_counter_dirpath,dst_jsonpath=char_and_span_counter_jsonpath)

    print(f'多进程处理的repo内的所有语言 language_set_inall={language_set_inall}')
    stack_group_num_range_2_counter_inall_asc=sorted(stack_group_num_range_2_counter_inall.items(),key=lambda x:x[0],reverse=False)
    print('*********写入所有文件路径如下**************')
    for write_jsonpath_iter in write_jsonpath_inall_all_process:
        print(write_jsonpath_iter)
    print('**********根据区间划分stack group后,按照group node num 正排,打印各个区间的数量************')
    num_1_counter=stack_group_num_range_2_counter_inall.get(1,None)
    print(f'1个文件的graph node数量={num_1_counter}')
    for check_stack_group_num_range_2_counter in  stack_group_num_range_2_counter_inall_asc:
        print(check_stack_group_num_range_2_counter)
    print('************各种方式过滤、fim处理的统计指标***********')
    for filter_name,counter_iter  in fileter_counter_dict_inall.items():
        print(filter_name,counter_iter)
    print('************grammar_name_2_counter_dict***********')
    grammar_name_2_counter_dict_inall_desc=sorted(grammar_name_2_counter_dict_inall.items(),key=lambda x:x[1],reverse=True)
    for grammar_name_counter_tuple_iter in grammar_name_2_counter_dict_inall_desc:
        print(grammar_name_counter_tuple_iter)



if __name__=='__main__':
    args=get_argparse()
    pprint_args(args=args)    
    if socket.gethostbyname(socket.gethostname())=='192.168.4.60':
        os.environ['GRAPH_FILE_MAX_SIZE']=str(1000*10000)
        os.environ['GRAPH_CONTENT_MAX_SIZE']=str(100000)
        os.environ['INNER_MULTI_CONTENT_NUM_THRES']=str(5)
        os.environ['WORK_ENV']='local'
        process_num=1
        pass
    else:
        os.environ['GRAPH_FILE_MAX_SIZE']=str(5000*10000)
        os.environ['GRAPH_CONTENT_MAX_SIZE']=str(1000000)
        os.environ['INNER_MULTI_CONTENT_NUM_THRES']=str(100)
        os.environ['WORK_ENV']='LPAI'
        process_num=multiprocessing.cpu_count()

    src_dirpath_list=args.src_dirpath_list.split(',')
    os.environ['alphanum_ratio'] = str(args.alphanum_ratio)
    os.environ['max_line_number'] = str(args.max_line_number)
    os.environ['bool_no_parser_with_normal'] = str(args.bool_no_parser_with_normal)
    print('debug bool_no_parser_with_normal 实际是否一致',os.environ['bool_no_parser_with_normal'].lower()=='true')
    # write_department_info(src_dirpath_list=src_dirpath_list,write_dirpath=args.write_dirpath)
    multi_process_repos(dataset_path_after_dedup=args.dataset_path_after_dedup,
                        write_dirpath=args.write_dirpath,args=args,
                        process_num=process_num)

    process_args_jsonpath=PathTemplate.process_args_jsonpath.format(write_dirpath=args.write_dirpath)
    print(f'process_args_jsonpath={process_args_jsonpath}')
    with open(process_args_jsonpath,'w') as fw:
        print_args={**os.environ,**vars(args)}
        json.dump(print_args,fw,indent=4,ensure_ascii=False)

