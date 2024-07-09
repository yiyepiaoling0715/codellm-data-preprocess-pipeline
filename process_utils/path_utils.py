import os
import json
import pandas as pd
from typing import List,Dict,Text
import re
from process_utils.constants import PathTemplate,FILES_DIRPATH,FileterCounter
from process_utils.dedup_content import CommonPattern
from process_utils.lang_processor import LangJudge
from process_utils.constants import Constants

#**************path处理**************

def get_group_repos_mark(project_root,last_n=3,group_name=''):
    # last_n_dir='_'.join(path.split('/')[-1*last_n:])
    # if group_name:
    #     return f'{group_name}_{last_n_dir}'
    # return last_n_dir
    last_n_dir_str    ='_'.join(project_root.split('/')[-1*last_n:])
    extra_path_str='/'.join(project_root.split('/')[:-1*last_n])
    return {'last_n_dir_str':last_n_dir_str,'extra_path_str':extra_path_str}

def get_projects_dirpath_list(src_dirpath_list,write_dirpath):
    """
        获取group路径下 所有repo的路径,并和write_dirpath组装为可tuple_list
        每个elem是repo维度的
    """
    src_dst_path_tuple_list=[]
    for src_dirpath_iter in src_dirpath_list:
        # group_mark=get_group_repos_mark(src_dirpath_iter)
        # write_dirpath_iter=os.path.join(write_dirpath,group_mark)
        write_dirpath_iter=write_dirpath
        # if os.path.exists(write_dirpath_iter):
        #     shutil.rmtree(write_dirpath_iter)
        os.makedirs(write_dirpath_iter,exist_ok=True)
        #约定路径格式 .../department/project_name
        department=src_dirpath_iter.split('/')[-2]
        project_names=os.listdir(src_dirpath_iter)
        ##已经包括了 department+project_name
        for project_name in project_names:
            project_path=os.path.join(src_dirpath_iter,project_name)
            print('project_path=',project_path)
            src_dst_path_tuple=(project_path,write_dirpath_iter,project_name,department)
            src_dst_path_tuple_list.append(src_dst_path_tuple)
    return src_dst_path_tuple_list  

def split_path_by_sep(filename):
    bool_split=False
    if '/' in filename:
        filename_parts=filename.split('/')
        bool_split=True
    elif "\\" in filename:
        filename_parts=re.escape(filename).split('\\')
        bool_split=True
    else:
        filename_parts=[filename]
    return bool_split,filename_parts

def filter_dirpath(root):
    """
        不仅仅是project_root,还包括 各级目录
    """
    if root and '.git' in root:
        return False
    bool_split,path_parts=split_path_by_sep(filename=root)
    for path_part_iter in path_parts:
        if path_part_iter and path_part_iter.startswith(('.','_')):
            # print(f'目录里边带.的路径 path_part_iter={path_part_iter},root={root}')
            return False
    return True

def filter_filanames(files,bool_counter=False):
    """
        过滤掉无效文件
    """
    filter_files=[]
    for file_iter in files:
        # python _xx.py 合理的
        # if file_iter and file_iter.startswith(('.','_')):
        if file_iter and file_iter.startswith('.'):
            if bool_counter:
                FileterCounter.filter_file_by_name+=1
            continue
        filter_files.append(file_iter)
    return filter_files


def find_all_filenames_from_root(root_dir,bool_counter=False):
    filepaths=[]
    for root, dirs, filenames in os.walk(root_dir):
        if not filter_dirpath(root):
            if bool_counter:
                FileterCounter.filter_dir_by_name+=1
            continue
        filter_filenames_iter=filter_filanames(files=filenames,bool_counter=bool_counter)
        for filename in filter_filenames_iter:
            filepath_iter=os.path.join(root, filename)
            filepaths.append(filepath_iter)
    return filepaths

# filepath_2_imports_dict
def complete_filepath_of_filepath_2_imports_dict(filepath_2_imports_dict:Dict[Text,List],language:Text):
    expand_filepath_2_imports_dict={}
    for parent_filepath_iter,import_name_2_path_dict_iter in filepath_2_imports_dict.items():
        if parent_filepath_iter not in expand_filepath_2_imports_dict.keys():
            expand_filepath_2_imports_dict[parent_filepath_iter]={}
        for import_name,path_iter in import_name_2_path_dict_iter.items():
            filepaths_iter=[]
            # for path_iter in dirpaths_iter:
            assert os.path.isdir(path_iter)
            filenames=os.listdir(path_iter)
            for filename in filenames:
                if not LangJudge.bool_file_match_lang(language=language,filename=filename):
                    continue 
                filepath_iter=os.path.join(path_iter, filename)
                filepaths_iter.append(filepath_iter)
            assert len(filepaths_iter)>=1
            assert import_name not in expand_filepath_2_imports_dict[parent_filepath_iter].keys()
            expand_filepath_2_imports_dict[parent_filepath_iter][import_name]=filepaths_iter
            try:
                check_max_file_num=200 if language in [Constants.LANG_Go] else 50
                assert len(filepaths_iter)<check_max_file_num
            except AssertionError as e:
                erro_msg=f'目录下文件过多,parent_filepath_iter={parent_filepath_iter},\nimport_name={import_name},len(filepaths_iter)={len(filepaths_iter)}'
                # for check_filepath_iter in filepaths_iter:
                #     print('check_filepath_iter=',check_filepath_iter)
                print(erro_msg)
    return expand_filepath_2_imports_dict


def find_filanme_2_paths_dict(root_dir,language,keep_filepaths_strategy='all'):
    """
        找出一个目录下存在的所有路径
    """
    filter_filepaths = []
    filanme_2_paths_dict={}
    file_counter=0
    filepaths=find_all_filenames_from_root(root_dir=root_dir,bool_counter=True)
    for filepath_iter in filepaths:
        # print(f'filepath_iter={filepath_iter}')
        filename=filepath_iter.split('/')[-1]
        if filename in ['utils_init.py']:
            print(f'utils_init.py filepath_iter={filepath_iter}')
        # print(f'root={root},file={file}')
        # print(f'filename={filename}')
        if not LangJudge.bool_file_match_lang(language=language,filename=filename):
            if filename in ['utils_init.py']:
                print(f'utils_init.py bool_file_match_lang continue')
            continue
        # filepath_iter=os.path.join(root, filename)
        # print('filepath_iter=',filepath_iter)
        if not os.path.isfile(filepath_iter):
            try:
                # assert os.path.isfile(filepath_iter),print(f'文件路径必须存在,filepath_iter={filepath_iter}')
                assert os.path.isfile(filepath_iter)
            except AssertionError as e:
                print(f'文件路径必须存在,filepath_iter={filepath_iter}')
            continue
        filter_filepaths.append(filepath_iter)
        if not filename in filanme_2_paths_dict.keys():
            filanme_2_paths_dict[filename]=[]                
        if keep_filepaths_strategy=='all':
            pass
        #todo del
        elif keep_filepaths_strategy=='testcase':
            if not judge_testcase_filename(filename=filename):
                continue
        else:
            raise ValueError(f'暂未支持keep_filepaths_strategy={keep_filepaths_strategy}')
        
        filanme_2_paths_dict[filename].append(filepath_iter)
        file_counter+=1
        if 'api-gateway.h' in filepath_iter:
            assert 'api-gateway.h' in filanme_2_paths_dict.keys(),print(f'filanme_2_paths_dict.keys()={filanme_2_paths_dict.keys()}')
    # if file_counter>10000:
        # break
    print(f'root_dir={root_dir},lang={language},所有相关文件数量 filter_filepaths={len(filter_filepaths)}')
    return filter_filepaths,filanme_2_paths_dict


def find_sub_dirname_2_paths_dict(root_dir,language):
    sub_dirname_2_paths_dict={}
    filepaths=find_all_filenames_from_root(root_dir=root_dir,bool_counter=True)
    for filepath_iter in filepaths:
        filename=filepath_iter.split('/')[-1]
        sub_dirname=filepath_iter.split('/')[-2]
        # print(f'root={root},file={file}')
        # print(f'filename={filename}')
        if not LangJudge.bool_file_match_lang(language=language,filename=filename):
            continue 
        sub_dirpath_iter=os.path.dirname(filepath_iter)
        assert sub_dirpath_iter.endswith(sub_dirname)
        if not sub_dirname in sub_dirname_2_paths_dict.keys():
            sub_dirname_2_paths_dict[sub_dirname]=set()
        sub_dirname_2_paths_dict[sub_dirname].add(sub_dirpath_iter)
        try:
            assert '.' not in sub_dirpath_iter
        except AssertionError as e:
            err_msg=f'.在dirpath里边,sub_dirpath_iter={sub_dirpath_iter}'
            print(err_msg)
            # raise ValueError(err_msg)

    for sub_dirname in sub_dirname_2_paths_dict.keys():
        sub_dirname_2_paths_dict[sub_dirname]=list(sub_dirname_2_paths_dict[sub_dirname])
    return sub_dirname_2_paths_dict


#**************content处理**************

def deal_repo_content_2_info_json(len_val_dict,content,project_name,filepaths,language,sample_truncate_serial_num):
    info_json={
        'project_name':project_name,
        'path':f'文件数量={len(filepaths)}--'+';'.join(filepaths[:5]),
        'content':content,
        'repository_name':project_name,
        'lang':language,
        "sample_truncate_serial_num":"_".join([str(flag_iter) for flag_iter in sample_truncate_serial_num]),

        **len_val_dict
    }
    return info_json

def write_department_info_by_path(src_dirpath_list,write_dirpath):
    # department_txtpath=os.path.join(write_dirpath,'departments.txt')
    department_txtpath=PathTemplate.department_txtpath.format(write_dirpath=write_dirpath)
    department_list=[]
    for src_dirpath_iter in src_dirpath_list:
            deparment_iter=src_dirpath_iter.split('/')[-2]
            department_list.append(deparment_iter)
    with open(department_txtpath,'w') as fw:
        for deparment_iter in department_list:
            fw.write(deparment_iter+'\n')
    print(f'department 写入路径={department_txtpath}')

def write_department_info_by_list(department_list,write_dirpath):
    """
        生成训练数据时候用,保存departments信息
    """
    department_txtpath=PathTemplate.department_txtpath.format(write_dirpath=write_dirpath)
    with open(department_txtpath,'w') as fw:
        for deparment_iter in department_list:
            fw.write(deparment_iter+'\n')
    print(f'department 写入路径={department_txtpath}')


def content_2_lines(content):
    lines = []
    current_line = []
    escaped = False  # 当前字符是否被转义
    string_char = None  # 当前字符串分界符，可以是一个引号或三个引号
    
    i = 0
    while i < len(content):
        char = content[i]

        # 检查当前是否在字符串内部
        if string_char is not None:
            if escaped:
                escaped = False
            else:
                if char == '\\':
                    escaped = True
                elif content[i:i + len(string_char)] == string_char:
                    # 字符串结束，跳过字符串结束符
                    i += len(string_char) - 1
                    string_char = None
        else:
            if char in ('"', "'"):
                # 检测三引号字符串
                triple_quote = content[i:i + 3]
                if triple_quote in ('"""', "'''"):
                    string_char = triple_quote
                    i += 2  # 跳过额外的两个引号
                else:
                    string_char = char
            elif char == '\n':
                # 在字符串外部遇到换行符，添加当前行并准备新行
                current_line.append(char)
                lines.append(''.join(current_line))
                current_line = []
                i += 1
                continue
        # 添加当前字符到当前行
        current_line.append(char)
        i += 1
        
    # 捕获文件结束后的最后一行
    if current_line:
        lines.append(''.join(current_line))
    # assert len(''.join(lines))==len(content),print(f"content_2_lines before len={len(content)},after len={len(''.join(lines))}")
    return lines


def info_json_list_deal_of_group_by_file_max_size(info_json_list:List[Dict])->List[List[str]]:
    """
        根据文件级别size 组成不同的 group info_json_str,每个group写入不同的info_json_str,用于写入不同的file
    """
    part_length=0
    info_json_str_list=[]
    part_info_json_str_list=[]
    for info_json_iter in info_json_list:
        info_json_str=json.dumps(info_json_iter,ensure_ascii=False)+'\n'
        part_info_json_str_list.append(info_json_str)
        part_length+=len(info_json_str)
        if part_length>int(os.environ['GRAPH_FILE_MAX_SIZE']):
            info_json_str_list.append(part_info_json_str_list)
            part_info_json_str_list=[]
            part_length=0
        else:
            pass
            # part_info_json_str_list.append(info_json_str)
    if part_info_json_str_list:
        info_json_str_list.append(part_info_json_str_list)
    return info_json_str_list


def split_current_content_by_line(content_window_size,current_context)->List[Text]:
    """
        按行遍历, 根据content_window_size 切分content,每个content都长度接近content_window_size
        return 窗口长度文本的list
    """
    line_set=()
    new_content_iter_slices=[]
    
    split_lines_list=[]
    split_lines_iter=[]

    cur_content_iter=''
    current_context_lines=current_context.split('\n')
    counter=0
    bool_break=False
    for index_line,line_iter in enumerate(current_context_lines):
        if len(cur_content_iter)<content_window_size or len(line_iter)<10:
            if counter==0:
                cur_content_iter=line_iter
            else:
                cur_content_iter=cur_content_iter+'\n'+line_iter
            bool_break=False
            split_lines_iter.append(line_iter+'\n')
        else:
            new_content_iter_slices.append(cur_content_iter+'\n')
            cur_content_iter=line_iter
            counter=0
            bool_break=True
            split_lines_list.append(split_lines_iter)
            split_lines_iter=[line_iter+'\n']
        counter+=1
    if cur_content_iter:
        assert len(split_lines_iter)>0
        lasst_content_iter=cur_content_iter + '\n' if bool_break else cur_content_iter
        new_content_iter_slices.append(lasst_content_iter)
        split_lines_iter[-1]=lasst_content_iter
        split_lines_list.append(split_lines_iter)
    new_content_after_split=''.join(new_content_iter_slices)
    check_length_after_split=len(new_content_after_split)
    if len(new_content_after_split)-len(current_context)==1:
        new_content_iter_slices[-1]=new_content_iter_slices[-1][:-1]
        split_lines_list[-1][-1]=split_lines_list[-1][-1][:-1]
    elif len(current_context)-len(new_content_after_split)==1:
        new_content_iter_slices[-1]=new_content_iter_slices[-1]+'\n'
        split_lines_list[-1][-1]=split_lines_list[-1][-1]+'\n'
    else:
        pass
    new_content_after_split=''.join(new_content_iter_slices)
    check_length_after_split=len(new_content_after_split)
    try:
        assert check_length_after_split==len(current_context),print(f'check_length_after_split={check_length_after_split},len(current_context)={len(current_context)}')
    except AssertionError as e:
        # max_len_text,min_len_text=new_content_after_split,current_context if len(new_content_after_split)>len(current_context) else current_context,new_content_after_split
        if len(new_content_after_split)>len(current_context):
            max_len_text,min_len_text=new_content_after_split,current_context  
        else:
            max_len_text,min_len_text=current_context,new_content_after_split
        min_len_text=min_len_text+'*'
        last_chars=list(zip(max_len_text[-50:],min_len_text[-50:]))
        print(f'ERROR last_chars={last_chars}')
        print(f'ERROR length mismatch new_content_after_split={new_content_after_split[-50:]},current_context={current_context[-50:]}')
        print(f'ERROR length mismatch new_content_after_split={new_content_after_split[-50:]},current_context={current_context[-50:]}')
        # for index in range(check_length_after_split):
        #     if new_content_after_split[index]!=current_context[index]:
        #         print('char 不匹配',index,new_content_after_split[index],current_context[index])
        # # raise ValueError('error')
    assert len(new_content_iter_slices)==len(split_lines_list)
    return new_content_iter_slices,split_lines_list


def split_current_context_by_window(content_window_size,current_context):
    new_content_iter_slices=[]
    window_num=math.ceil(len(current_context)/content_window_size)
    for window_num_iter in range(window_num):
        new_content_iter_slice_iter=current_context[window_num_iter*content_window_size:(window_num_iter+1)*content_window_size]
        new_content_iter_slices.append(new_content_iter_slice_iter)
    assert len(''.join(new_content_iter_slices))==len(current_context)
    return new_content_iter_slices

def read_code_file_as_list(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    lines=content_2_lines(content=content)
    return lines
 
def read_dpend_filepath_from_cpp_compile_fielpath(filepath,root_dir):
    root_dir=root_dir.rstrip('/') if root_dir.endswith('/') else root_dir
    project_name=root_dir.split('/')[-1]
    sub_root_names=os.listdir(root_dir)

    # before_project_name_dirpath='/'.join(root_dir.split('/')[:-1])
    with open(filepath, 'r', encoding='utf-8') as fr:
        abs_depend_path_list=[]
        for line in fr:
            #line 18 "./../../Projects/TC389_Demo/Cfg_Prj/GenData_DEBUG/Os/MemMap.h"
            if not line.startswith('#line'):
                continue
            searcher=CommonPattern.extract_depend_path_pattern.search(line)
            extract_path=searcher.group(1)
            # if extract_path.startswith('/'):
            if extract_path.startswith('/opt'):
                ##todo docker内编译后加上
                # print(f'编译后为绝对路径={extract_path},当前文件路径={filepath}')
                continue
            enter_str=''
            if extract_path.startswith('/'+project_name):
                enter_str='enter in startwith project_name'
                path_suffix=extract_path.replace('/'+project_name+'/','')
                # print(f'enter in extract_path,before_project_name_dirpath={before_project_name_dirpath},extract_path={extract_path}')
                # abs_depend_path_iter=os.path.join(before_project_name_dirpath,extract_path)
                # print(f'project_name={project_name},extract_path={extract_path},\npath_suffix={path_suffix}')    
            elif extract_path.startswith('/') and extract_path.split('/')[1] in sub_root_names:
                enter_str='enter in startwith sub_root_names'
                path_suffix='/'.join(extract_path.split('/')[2:])
                
            else:
                enter_str='enter else'
                # print('enter in else')
                upper_counter=extract_path.count('../')
                path_suffix=extract_path.replace('../','').replace('./','')
                # prefix_path='/'.join(filepath.split('/')[:-1*upper_counter])
                # abs_depend_path_iter=os.path.join(prefix_path,path_suffix)
            abs_depend_path_iter=os.path.join(root_dir,path_suffix)
            # print(abs_depend_path_iter)
            print_info1=f"extract_path={extract_path}\n,extract_path[0]={extract_path.split('/')[1]},sub_root_names={sub_root_names},\n"
            print_info2=f'project_name={project_name},extract_path={extract_path},\npath_suffix={path_suffix},\nroot_dir={root_dir}\n'
            print_info3=f'abs_depend_path_iter={abs_depend_path_iter}'
            assert os.path.exists(abs_depend_path_iter),print(print_info1+print_info2+print_info3)    

            abs_depend_path_list.append(abs_depend_path_iter)
        dedeup_abs_depend_path_list=[]
        for abs_depend_path_iter in abs_depend_path_list:
            if abs_depend_path_iter not in dedeup_abs_depend_path_list:
                dedeup_abs_depend_path_list.append(abs_depend_path_iter)
        assert len(dedeup_abs_depend_path_list)<=len(abs_depend_path_list)
        assert len(set(dedeup_abs_depend_path_list).intersection(set(abs_depend_path_list)))==len(dedeup_abs_depend_path_list)
        return {filepath:dedeup_abs_depend_path_list}

def get_filepath_2_depend_filepath_list_dict_after_cpp_compile(root_dir):
    filepath_2_filepath_list_dict={}
    for root,dirs,filenames in os.walk(root_dir):
        if not filter_dirpath(root):
                continue
        filter_filenames=filter_filanames(files=filenames)
        for filename in filter_filenames:
            filepath=os.path.join(root,filename)
            if not filename.endswith('.i'):
                continue
            filepath_2_depend_filepath_list_dict_iter=read_dpend_filepath_from_cpp_compile_fielpath(filepath=filepath,root_dir=root_dir)
            
            assert filepath not in filepath_2_filepath_list_dict.keys()
            filepath_2_filepath_list_dict.update(filepath_2_depend_filepath_list_dict_iter)
    filepath_list=[filepath_iter for filepath_iter in list(filepath_2_filepath_list_dict.keys())]
    prefix_path_set=set()
    for filepath_iter in filepath_list:
        prefix_path='/'.join(filepath_iter.split('/')[:8])
        prefix_path_set.add(prefix_path)
    for prefix_path_iter in prefix_path_set:
        print('读取过的目录 prefix_path_iter=',prefix_path_iter)
    return filepath_2_filepath_list_dict

def read_xlsx_of_testcase_note():
    excelpath=os.path.join(FILES_DIRPATH,'测试用例导出-车控OS.xlsx')
    st=pd.read_excel(excelpath,sheet_name='测试用例导出-车控OS')
    test_name_column=st['名称']
    test_point_column=st['测试点']
    test_steps_column=st['测试步骤']

    test_signature_2_info_dict={}
    for index,test_name_iter in enumerate(test_name_column):
        test_point_iter=test_point_column[index]
        test_steps_iter=test_steps_column[index]
        test_signature_2_info_dict[test_name_iter]={
            'test_point':test_point_iter,
            'test_steps':test_steps_iter
        }
    return test_signature_2_info_dict
    

def get_filepaths_friom_root_dir(root_dir):
    filepath_list=[]
    for root, dirs, filenames in os.walk(root_dir):
        if not filter_dirpath(root):
            FileterCounter.filter_dir_by_name+=1
            continue
        filter_filenames_iter=filter_filanames(files=filenames)
        for filename in filter_filenames_iter:
            filepath_iter=os.path.join(root, filename)
            filepath_list.append(filepath_iter)
    return filepath_list






















        #     filter_filepaths = []
        # filanme_2_paths_dict={}
        # file_counter=0
        # for root, dirs, filenames in os.walk(root_dir):
        #     if not filter_dirpath(root):
        #         continue
        #     filter_filenames=filter_filanames(files=filenames)
        #     for filename in filter_filenames:
        #         # print(f'root={root},file={file}')
        #         # print(f'filename={filename}')
        #         if not LangJudge.bool_file_match_lang(language=self.language,filename=filename):
        #             continue
        #         filepath_iter=os.path.join(root, filename)
        #         # print('filepath_iter=',filepath_iter)
        #         if not os.path.isfile(filepath_iter):
        #             continue
        #         filter_filepaths.append(filepath_iter)
        #         if not filename in filanme_2_paths_dict.keys():
        #             filanme_2_paths_dict[filename]=[]




# def bool_keep_dirpath(dirpath):
#     if 'thirdparty' in dirpath.lower():
#         return False
#     return True    



# def split_current_content_by_line_wrong(content_window_size,current_context)->List[Text]:
#     """
#         按行遍历, 根据content_window_size 切分content,每个content都长度接近content_window_size
#         return 窗口长度文本的list
#     """
#     line_set=()
    
#     split_lines_list=[]
#     split_lines_iter=[]
#     new_content_iter_slices=[]
#     cur_content_iter=''

#     # current_context_lines=current_context.split('\n')
#     # current_context_lines=content_2_lines(content=current_context)
#     counter=0
#     bool_break=False
#     for index_line,line_iter in enumerate(current_context_lines):
#         if len(cur_content_iter)<content_window_size or len(line_iter)<10:
#             if counter==0:
#                 cur_content_iter=line_iter
#             else:
#                 # cur_content_iter=cur_content_iter+'\n'+line_iter
#                 cur_content_iter=cur_content_iter+line_iter
#             bool_break=False
#             # split_lines_iter.append(line_iter+'\n')
#             split_lines_iter.append(line_iter)
#         else:
#             # new_content_iter_slices.append(cur_content_iter+'\n')
#             new_content_iter_slices.append(cur_content_iter)
#             cur_content_iter=line_iter
#             counter=0
#             bool_break=True
#             split_lines_list.append(split_lines_iter)
#             # split_lines_iter=[line_iter+'\n']
#             split_lines_iter=[line_iter]
#         counter+=1
#     if cur_content_iter:
#         if len(current_context)<content_window_size and not new_content_iter_slices:
#             new_content_iter_slices=['']
#             split_lines_list=[[]]
#         assert len(split_lines_iter)>0
#         # lasst_content_iter=cur_content_iter + '\n' if bool_break else cur_content_iter
#         # lasst_content_iter=cur_content_iter 
#         new_content_iter_slices[-1]=new_content_iter_slices[-1]+cur_content_iter
#         # split_lines_iter[-1]=cur_content_iter
#         split_lines_list[-1]=split_lines_list[-1].extend(split_lines_iter)
#     new_content_after_split=''.join(new_content_iter_slices)
#     check_length_after_split=len(new_content_after_split)
#     try:
#         assert check_length_after_split==len(current_context),print(f'check_length_after_split={check_length_after_split},len(current_context)={len(current_context)}')
#     except AssertionError as e:
#         max_len_text,min_len_text=new_content_after_split,current_context if len(new_content_after_split)>len(current_context) else current_context,new_content_after_split
#         min_len_text=min_len_text+'*'
#         last_chars=list(zip(max_len_text[-50],min_len_text[-50:]))
#         print(f'last_chars={last_chars}')
#         print(f'length mismatch new_content_after_split={new_content_after_split[-50:]},current_context={current_context[-50:]}')
#         for index in range(check_length_after_split):
#             if new_content_after_split[index]!=current_context[index]:
#                 print('char 不匹配',index,new_content_after_split[index],current_context[index])
#         raise ValueError('error')
#     assert len(new_content_iter_slices)==len(split_lines_list)
#     return new_content_iter_slices,split_lines_list

