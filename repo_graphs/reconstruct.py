import os
import re
import abc
import time
import copy
import numpy as np
import collections
import codecs
from typing import Dict,Text,List
from process_utils.utils import timeit
from process_utils.lang_processor import LangJudge
from process_utils.path_utils import (
    filter_dirpath,
    filter_filanames,
    find_all_filenames_from_root,
    find_sub_dirname_2_paths_dict,
    find_filanme_2_paths_dict,
    complete_filepath_of_filepath_2_imports_dict
    )
from process_utils.treesitter_utils import extract_imports_with_parser
from repo_graphs.make_graph_of_dfs import PathNode,PathGraph
from process_utils.constants import Constants,FileterCounter
from process_utils.utils import merge_dict_dep_2_list_of_same_key
import numpy as np
from process_utils.utils import read_content_with_ignore_error
from process_utils.algo_utils import cacl_distance_by_jaccard_of_pair_wise,DependPathFounder,remove_personal_path_prefix
from process_utils.lang_processor import LangParserProxy
from process_utils.dedup_content import CommonPattern
import itertools
check_path_key_list=[]

check_filepath_list=[
                    ''
                    ]

def split_equal_filenames(span):
    split_pattern=re.compile('[,\n\t ]+')
    parts=split_pattern.split(span)
    parts=[part for part in parts if part not in ['(',')','']]
    return parts


class ParseBase(object):
    work_env=os.environ['WORK_ENV']
    lang_parse_proxy=LangParserProxy(work_env=work_env)

    def __init__(self,language,keep_filepaths_strategy='all'):
        self.language=language
        # testcase
        self.keep_filepaths_strategy=keep_filepaths_strategy
        self.corse_include_pattern=None

    def _find_filanme_2_paths_dict(self,root_dir):
        return find_filanme_2_paths_dict(root_dir=root_dir,language=self.language,keep_filepaths_strategy=self.keep_filepaths_strategy)
    
    def _find_sub_dirname_2_paths_dict(self,root_dir):
        return find_sub_dirname_2_paths_dict(root_dir=root_dir,language=self.language)

    ##todo filename2path,改为 part_path2abs_path, filename存在重复相同名字的
    def find_filepaths_no_suffix(self,root_dir):
        """
            将所有的文件路径,转为不带后缀的文件路径
            将所有的文件路径建立 {文件名:文件路径列表}的映射关系
        """
        filter_filepaths,filanme_2_paths_dict=self._find_filanme_2_paths_dict(root_dir=root_dir)
        #follow  header format
        # imp_2_paths_dict={filename.replace('.py',''):path_iter for filename,path_iter in filanme_2_paths_dict.items()}
        imp_2_paths_dict={filename.split('.')[0]:path_iter for filename,path_iter in filanme_2_paths_dict.items()}
        # imp_2_path_dict_of_init_=self._find_filepaths_of_init_(root_dir=root_dir)
        filanme_2_paths_dict_inall={**imp_2_paths_dict}
        for check_k,check_v in imp_2_paths_dict.items():
            # print(f'suffix_iter={LangJudge.lang_suffix_list_dict[self.language]},check_k={check_k}')
            for suffix_iter in LangJudge.lang_suffix_list_dict[self.language]:
                assert '.'+suffix_iter not in check_k
        sub_dirname_2_paths_dict=self._find_sub_dirname_2_paths_dict(root_dir=root_dir)
        return filter_filepaths,filanme_2_paths_dict_inall,sub_dirname_2_paths_dict

    # 步骤1: 搜集项目中的所有C++相关文件 {xx.cpp:filepath}
    def find_filepaths(self,root_dir):
        filter_filepaths,filanme_2_paths_dict=self._find_filanme_2_paths_dict(root_dir=root_dir)
        sub_dirname_2_paths_dict=self._find_sub_dirname_2_paths_dict(root_dir=root_dir)
        return filter_filepaths,filanme_2_paths_dict,sub_dirname_2_paths_dict
    
    def _extract_imports(self,filepath)->List[List[Text]]:
        """
            include 切分后的每部分都保留,作为List
        """
        content=read_content_with_ignore_error(filepath=filepath)
        if not content:
            return []
        # print(f'on include_pattern.findall,self.include_pattern={self.include_pattern}')
        includes=[]
        for include_pattern_iter in self.include_pattern:
            includes_iter = include_pattern_iter.findall(content)
            includes.extend(includes_iter)
        includes=list(set(includes))
        includes=[include_iter for include_iter in includes]
        # print('debug includes=')
        # assert len(includes)==1,print('includes num!=1,includes=\n',includes)
        # file_suffix='/'.join(file.split('/')[-3])
        # print(f'file_suffix={file_suffix},includes={includes}')
        new_includes=[]
        for include in includes:
            # if '/' in include:
            include_parts=tuple(include.split('/'))
            new_includes.append(include_parts)
        #for check begin
        if self.corse_include_pattern:
            corse_includes=[]
            for corse_include_pattern_iter in self.corse_include_pattern:
                includes_iter = corse_include_pattern_iter.findall(content)
                corse_includes.extend(includes_iter)
            try:
                assert len(set(corse_includes))in [len(includes),len(includes)+1]
            except AssertionError as e:
                # corse_includes=[elem.strip('<>"') for elem in corse_includes]
                diff_corse=set(corse_includes).difference(set(includes))
                # print('includes=',includes)
                # print('corse_includes=',set(corse_includes))
                for check_index_1 in range(len(corse_includes)):
                    bool_in=False
                    for check_index_2 in range(len(includes)):
                        if includes[check_index_2] in corse_includes[check_index_1]:
                            bool_in=True
                            break
                    if not bool_in:
                        print(f'include提取数量不对\n,filepath={filepath},\nlen(corse_includes)={len(set(corse_includes))},len(includes)={len(includes)}')
                        print(f'独有的include={corse_includes[check_index_1]}')
                    # print(f'corse_includes={corse_includes[check_index]},includes={includes[check_index]}')
                # raise ValueError('error')
            # if np.random.random()<0.01:
            # print(f'filepath={filepath},\nlen(corse_includes)={len(corse_includes)},len(includes)={len(includes)}')
        #for check end
        return new_includes

    def extract_imports(self,filepath)->List[List[Text]]:
        import_tuple_list=self._extract_imports(filepath=filepath)
        import_tuple_list=list(set(import_tuple_list))
        import_tuple_list=[list(elem) for elem in import_tuple_list]
        return import_tuple_list



    def find_import_paths(self,imports:List[List[Text]],filanme_2_paths_dict,project_root,import_src_filepath=None):
        """
            根据解析的头文件str,通过精准匹配/模糊匹配,找到对应的文件路径
        """
        import_2_path_dict={}
        for imp_tuple_iter in imports:
            #以最后一个文件名作为判断的标志
            try:
                filename=imp_tuple_iter[-1]
            except IndexError as e:
                error_msg=f'imp_tuple_iter={imp_tuple_iter},\nimport_src_filepath={import_src_filepath}'
                raise ValueError(error_msg)
            # prefix_parts=imp_tuple_iter[:-1] if len(imp_tuple_iter)>1 else []
            if filename not in filanme_2_paths_dict.keys():
                pass
            else:
                paths=filanme_2_paths_dict[filename]
                if len(paths)==1:
                    import_2_path_dict[filename]=paths[0]
                    FileterCounter.counter_import_name_2_path_eq_1+=1
                else:
                    FileterCounter.counter_import_name_2_path_gt_1+=1
                    most_match_path=DependPathFounder.pick_most_match_path(imports=imp_tuple_iter,
                                                                import_src_filepath=import_src_filepath,
                                                                paths=paths,
                                                                project_root=project_root,
                                                                language=self.language)
                    import_2_path_dict[filename]=most_match_path
                    # if len(imp_tuple_iter)>1 and filename not in ['utils']:
                    #     print(f'*****************\nfilename={filename}')
                    #     print(f'import_src_filepath=\t{import_src_filepath}')
                    #     print(f'most_match_path=\t{most_match_path}')
                    #     for check_path in paths:
                    #         print(f'候选path={check_path}')
        return import_2_path_dict

    def create_repo_import_dict(self,project_root)->Dict[Text,Dict[Text,Text]]:
        ts1=time.time()
        # 遍历仓库路径，找到所有的Python文件
        filter_filepaths,filename_2_paths_dict,sub_dirname_2_paths_dict = self.find_filepaths(project_root)
        # for check_filename,paths_iter in filanme_2_paths_dict.items():
            # if len(paths_iter)>1:
            #     print(f'check_filename={check_filename},paths_iter={paths_iter}')
        # for python_file in python_files:
        #     print(os.path.isfile(python_file),python_file)
        ts2=time.time()
        filepath_2_import_name_2_path_dict_of_file={}
        if 'filepath' in self.import_path_type_list:
            filepath_2_import_name_2_path_dict_of_file=self.create_filepath_2_import_name_2_path_dict(
                        filter_filepaths=filter_filepaths,
                        filanme_2_paths_dict=filename_2_paths_dict,
                        project_root=project_root)
            check_filepath_list=[check_elem for check_elem in filter_filepaths if check_elem in ['xx']]
            # print(f'check_filepath_list={check_filepath_list}')
        expand_filepath_2_import_name_2_path_dict={}
        if 'dirpath' in self.import_path_type_list:
            filepath_2_import_name_2_path_dict_of_dir=self.create_filepath_2_import_name_2_path_dict(
                        filter_filepaths=filter_filepaths,
                        filanme_2_paths_dict=sub_dirname_2_paths_dict,
                        project_root=project_root)
            expand_filepath_2_import_name_2_path_dict=complete_filepath_of_filepath_2_imports_dict(
                                filepath_2_imports_dict=filepath_2_import_name_2_path_dict_of_dir,
                                language=self.language)
        filepath_2_import_name_2_path_dict=merge_dict_dep_2_list_of_same_key(
                [filepath_2_import_name_2_path_dict_of_file,expand_filepath_2_import_name_2_path_dict],
                project_root=project_root,language=self.language)
        

        ts3=time.time()
        time_cost_dict={
            'reate_repo_import_dict find_filepaths  ts2_1':ts2-ts1,
            'for extract_imports  ts3_2':ts3-ts2
        }
        for time_k,time_v in time_cost_dict.items():
            if time_v>100:
                print(f'extract_imports  耗时 >100 {time_k}:{time_v}')
        # print('**************dependencies*****************')
        # for filepath_iter,includes_iter in file_2_imports_dict.items():
        #     file_suffix='/'.join(filepath_iter.split('/')[-3:])
            # print(f'file_suffix={file_suffix},includes={includes_iter}')
        all_paths=set()
        for filepath_iter,include_name_2_include_path_iter in filepath_2_import_name_2_path_dict.items():
            
            with open(filepath_iter,'r',encoding='utf-8') as fr:
                try:
                    file_content=fr.read()
                except UnicodeDecodeError as e:
                    pass
                bool_cpp=LangJudge.get_language_of_file(filepath_iter) in [Constants.LANG_CPP]
            for include_name_iter,include_path_iter in include_name_2_include_path_iter.items():
                if not bool_cpp:
                    try:
                        assert include_name_iter in file_content
                    except AssertionError as e:
                        print(f'include_name不在文件内容中,filepath_iter={filepath_iter} include_name_iter={include_name_iter}')
                if isinstance(include_path_iter,list):
                    all_paths.update(include_path_iter)
                    for include_path_iter_iter in include_path_iter:
                        assert include_name_iter in include_path_iter_iter
                elif os.path.isfile(include_path_iter):
                    all_paths.add(include_path_iter)
                    assert include_name_iter in include_path_iter
                else:
                    raise ValueError('error')
            # all_paths.update(include_name_2_include_path_iter.values())
            all_paths.add(filepath_iter)
        # print(f'language={self.language},filter_filepaths数量={len(filter_filepaths)}')
        # print(f'language={self.language},all_paths数量={len(all_paths)}')
        # print(f'language={self.language},file_2_imports_dict数量={len(filepath_2_imports_dict)}')
        try:
            assert len(all_paths)==len(filter_filepaths)==len(filepath_2_import_name_2_path_dict)
        except AssertionError as e:
            err_msg=f'language={self.language},filter_filepaths数量={len(filter_filepaths)},all_paths数量={len(all_paths)},file_2_imports_dict数量={len(filepath_2_imports_dict)}'
            all_paths_unique_part=set(all_paths).difference(set(filter_filepaths))
            for all_paths_unique_iter in all_paths_unique_part:
                print(f'all_paths_unique_iter={all_paths_unique_iter}')
            raise ValueError(err_msg)
        #check begin
        for check_path_key_iter in check_path_key_list:
            print(f'check_path_key_iter={check_path_key_iter},\nfilepath_2_imports_dict={filepath_2_import_name_2_path_dict[check_path_key_iter]}')
        filepath_2_import_counter={k:len(v) for k,v in filepath_2_import_name_2_path_dict.items()}
        import_counter=collections.Counter(filepath_2_import_counter.values())
        print('文件内的import_counter数量排序',import_counter.most_common(50))
        #check end
        return filepath_2_import_name_2_path_dict

    def create_filepath_2_import_name_2_path_dict(self,filter_filepaths,filanme_2_paths_dict,project_root):
        # # 解析每个文件的import
        filepath_2_import_name_2_path_dict = {}
        for filepath_iter in filter_filepaths:
            imports_iter = self.extract_imports(filepath_iter)
            if imports_iter:
                # 匹配import路径
                # import_paths = self.find_import_paths(imports, project_root)
                try:
                    import_name_2_path_dict_iter = self.find_import_paths(
                                                imports=imports_iter,
                                                filanme_2_paths_dict=filanme_2_paths_dict,
                                                import_src_filepath=filepath_iter,
                                                project_root=project_root)
                    # print(f'imports_iter={imports_iter},import_name_2_path_dict_iter={import_name_2_path_dict_iter}')
                except ValueError as e:
                    print(f'filepath_iter={filepath_iter},imports_iter={imports_iter}')
                    error_info=f'error={e.args},\nfilepath_iter={filepath_iter},\n从一个文件抽取的所有imports_iter={imports_iter}'
                    raise ValueError(error_info)
                filepath_2_import_name_2_path_dict[filepath_iter] = import_name_2_path_dict_iter
                FileterCounter.counter_has_import_file+=1
            elif not imports_iter :
                if os.path.getsize(filepath_iter)>1000 and filepath_iter.split('.')[-1] in LangJudge.get_supported_parser_include_suffix_list():
                    print('没有include filepath=\t',filepath_iter)
                filepath_2_import_name_2_path_dict[filepath_iter] = {}
                FileterCounter.counter_no_import_file+=1
            else:
                #todo 加入 无import文件的处理
                pass
            if filepath_iter=='xxx':
                print(f'util/utils_init.py imports_iter={imports_iter},import_name_2_path_dict_iter={import_name_2_path_dict_iter}')       
        return filepath_2_import_name_2_path_dict


class ParsePython(ParseBase):
    def __init__(self):
        # super(ParsePython,self).__init__(language='python')
        super(ParsePython,self).__init__(language=Constants.LANG_PYTHON)
        # 正则表达式匹配Python的import语句
        # self.import_pattern = re.compile(r'^\s*(from\s+(|.)(\w+(\.\w+)*)\s+import|import\s+(\w+(\.\w+)*))')
        self.include_pattern=[re.compile(r'^\s*(from\s+[\.]{0,}(\w+(\.\w+)*)\s+import|import\s+(\w+(\.\w+)*))'),
                            #   re.compile(r'^\s*(from\s+\.\s+import\s+(\w+))')
                            re.compile(r'^\s*(from\s+(.*?)\s+import\s+([0-9a-zA-Z,_ ]+)|)'),
                            re.compile(r'^\s*(from\s+(.*?)\s+import\s+\(([0-9a-zA-Z,_\t \n]+)\))'),

                              ]
        self.import_path_type_list=['filepath','dirpath']
    def _extract_imports_with_tree_sitter(self,filepath)->List[List[Text]]:
        cur_file_lang=LangJudge.get_language_of_file(filepath=filepath)
        if not cur_file_lang:
            print(f'ERROR cur_file_lang=None,filepath={filepath}')
            return []
        # print('cur_file_lang=',cur_file_lang)
        parser=self.lang_parse_proxy.get_parser(lang=cur_file_lang)

        import_node_list=extract_imports_with_parser(filepath=filepath,parser=parser)
        includes=[]
        import_parts_inall_for_check=[]
        for import_node_iter in import_node_list:
            node_text_iter=codecs.decode(import_node_iter.text,'utf-8')
            import_parts=CommonPattern.general_import_keywords_pattern.split(node_text_iter)
            # print(f'node_text_iter={node_text_iter},import_parts={import_parts}')

            import_parts=[part.strip('\r\n ') for part in import_parts if part]
            import_parts_inall_for_check.append(import_parts)
            new_import_parts=[]
            bool_comma=False
            for index_part,import_part_iter in enumerate(import_parts):
                if ','  in import_part_iter:
                    import_part_iter=CommonPattern.import_common_replace_pattern.sub(')',import_part_iter)
                    try:
                        assert index_part==len(import_parts)-1
                    except AssertionError as e:
                        err_msg=f'AssertionError filepath={filepath},\nindex_part={index_part},len(import_parts)-1={len(import_parts)-1},import_node_iter={import_node_iter},\nimport_parts={import_parts}'
                        # raise ValueError()
                        print(err_msg)
                    # gen_last_part_list=split_equal_filenames(import_parts[-1])
                    gen_last_part_list=split_equal_filenames(import_part_iter)
                    new_import_parts.append(gen_last_part_list)
                    # print('gen_last_part_list=',gen_last_part_list)
                    bool_comma=True
                    # for new_part_iter in gen_last_part_list:
                        # new_import_parts_iter=import_parts[:-1]+[new_part_iter]
                        # new_import_parts.extend(new_import_parts_iter)
                        # includes.append(new_import_parts_iter)
                    # includes.append(import_parts[:-1])
                    continue
                if '.' in import_part_iter:
                    split_part_iter=import_part_iter.split('.')
                    new_import_parts.extend(split_part_iter[:-1])
                    cur_last_part=split_part_iter[-1]
                else:
                    cur_last_part=import_part_iter
                
                # elif CommonPattern.import_as_pattern.search(import_parts[-1]):
                if CommonPattern.import_as_pattern.search(cur_last_part):
                    inlude_part=CommonPattern.import_as_pattern.split(cur_last_part)[0]
                    # new_import_parts=import_parts[:-1]+[inlude_part]
                    # print('as add',import_parts[:-1]+[inlude_part])
                    # includes.append(new_import_parts)
                    new_import_parts.append(inlude_part)
                else:
                    new_import_parts.append(cur_last_part)
            if len(new_import_parts)>1:
                includes.append(new_import_parts[:-1])
            if bool_comma:
                new_import_parts_copy=[]
                copy_num=len(new_import_parts[-1])
                try:
                    assert copy_num>1
                except AssertionError as e:
                    err_msg=f'有,但是为单个import, filepath={filepath},\n node_text_iter={node_text_iter},\n new_import_parts={new_import_parts}'
                    print(err_msg)
                    # raise ValueError()
                for index_copy_index in range(copy_num):
                    new_import_parts_iter=new_import_parts[:-1]+[new_import_parts[-1][index_copy_index]]
                    new_import_parts_copy.append(new_import_parts_iter)
            else:
                new_import_parts_copy=[new_import_parts]
            includes.extend(new_import_parts_copy)    
        if filepath in check_filepath_list:
            print(f'check filepath={"/".join(filepath.split("/")[-5:])} includes={includes},\nimport_parts_inall_for_check={import_parts_inall_for_check}')
        new_includes=[]
        for include in includes:  
            new_include_iter=[]
            for part in include:
                if isinstance(part,list):
                    new_include_iter.extend(part)
                elif part:
                    new_include_iter.append(part)
            new_include_iter=[elem.strip(' \r\n') for elem in new_include_iter if elem.strip(' \r\n')]
            if not new_include_iter:
                continue
            new_include_iter=tuple(new_include_iter)
            new_includes.append(new_include_iter)
        return new_includes

    def _extract_imports_with_re(self,filepath)->List[List[Text]]:
                # 获取文件中的所有import语句
        try:
            # with open(file_path, 'r',encoding='utf-8',errors='ignore') as fr:
            with open(filepath, 'r',encoding='utf-8',errors='strict') as fr:
                imports = []
                for line in fr.readlines():
                    for index_pattern,import_patter_iter in enumerate(self.include_pattern):
                        match = import_patter_iter.match(line.strip())
                        if match:
                            searcher=import_patter_iter.search(line.strip())
                            # 提取导入模块，对于from ... import ...情况提取第一个分组
                            matched_group = match.group(2) if match.group(2) else match.group(4)
                            imports.append(matched_group)
                            if filepath in check_path_key_list:  
                                print(f' filepath={filepath},imports={matched_group}')
                            break
                # if 'parser/com/conftest.py' in file_path:
                # if 'test_sys_test.py' in file_path:
                if 'asio-server/conanfile.py' in filepath:
                    print(f'extract_imports filepath={filepath},imports={imports}')
            #对齐通用imorts处理方式
            new_imports=[_import.split('.') for _import in imports]
            
            if filepath in check_path_key_list:
                print(f'extract_imports filepath={filepath},imports={imports}')
            return new_imports
        except UnicodeDecodeError as e:
            print(f'ParsePython extract_imports UnicodeDecodeError when open filepath={filepath}')
            print('error head 100=',str(e.args)[:100],'error tail 100=',str(e.args)[-100:])
            return []
    
    def extract_imports(self,filepath)->List[List[Text]]:

        import_tuple_list=self._extract_imports_with_tree_sitter(filepath=filepath)
        if not import_tuple_list:
            return []
        import_tuple_list_asc=sorted(list(set(import_tuple_list)),key=lambda x:len(x),reverse=False)
        import_tuple_list_asc=[list(elem) for elem in import_tuple_list_asc]
        return import_tuple_list_asc

    def _replace_suffix_for_filanme_2_paths_dict(self,filanme_2_paths_dict):
        imp_2_paths_dict={filename.replace('.py',''):paths_iter for filename,paths_iter in filanme_2_paths_dict.items()}
        for check_k,check_v in imp_2_paths_dict.items():
            assert '.py' not in check_k
        return imp_2_paths_dict

    def find_filepaths(self,root_dir):
        filter_filepaths,filanme_2_paths_dict=self._find_filanme_2_paths_dict(root_dir=root_dir)
        imp_2_paths_dict=self._replace_suffix_for_filanme_2_paths_dict(filanme_2_paths_dict=filanme_2_paths_dict)
        #follow  header format
        sub_dirname_2_paths_dict=self._find_sub_dirname_2_paths_dict(root_dir=root_dir)
        return filter_filepaths,imp_2_paths_dict,sub_dirname_2_paths_dict

class ParseCpp(ParseBase):
    def __init__(self):
        self.include_pattern = [re.compile(r'#include\s+"(.+)"'), re.compile(r'#include\s+<(.+)>')]
        # super(ParseCpp,self).__init__('cpp')
        super(ParseCpp,self).__init__(Constants.LANG_CPP)
        self.corse_include_pattern=[re.compile('#include(.*)')]
        self.import_path_type_list=['filepath']

    def extract_imports(self,filepath)->List[List[Text]]:
        import_tuple_list:List[List[Text]]=self._extract_imports(filepath=filepath)
    
        if not import_tuple_list:
            return []
        import_tuple_list=list(set(import_tuple_list))
        import_tuple_list=[list(elem) for elem in import_tuple_list]

        new_includes=[]
        for include_tuple_iter in import_tuple_list:
            new_includes.append(include_tuple_iter)
            if filepath.endswith(('.h','.hpp')):
                break
            file_suffix_tuple_list=[['.h','.c'],['.hpp','.cpp']]
            bool_copy=False
            for file_suffix_tuple_iter in file_suffix_tuple_list:
                if include_tuple_iter[-1].endswith(file_suffix_tuple_iter[0]):
                    copy_include_tuple_iter=copy.deepcopy(include_tuple_iter)
                    copy_include_tuple_iter[-1]=copy_include_tuple_iter[-1].replace(file_suffix_tuple_iter[0],file_suffix_tuple_iter[1])
                    # new_includes.append(include_tuple_iter)
                    if copy_include_tuple_iter[-1] in filepath:
                        break
                    assert copy_include_tuple_iter[-1].endswith(('.c','cpp'))
                    new_includes.append(copy_include_tuple_iter)
                    bool_copy=True
                    break
        if filepath.endswith(('.h','.hpp')):
            for check_include_iter in new_includes:
                try:
                    assert check_include_iter[-1].endswith(('.h','hpp')) 
                except AssertionError as e:
                    error_msg=f'.h/.hpp结尾的,有无后缀的include, check_include_iter={check_include_iter},filepath={filepath}'
                    # raise ValueError(error_msg)
        return new_includes

class ParseC(ParseBase):
    def __init__(self):
        # super(ParseCpp,self).__init__('cpp')
        super(ParseC,self).__init__(Constants.LANG_C)
        self.include_pattern = [re.compile(r'#include\s+"(.+)"'), re.compile(r'#include\s+<(.+)>')]
        self.import_path_type_list=['filepath']

class ParserGo(ParseBase):
    def __init__(self):
        # super(ParserGo,self).__init__('go')
        super(ParserGo,self).__init__(Constants.LANG_Go)
        # self.include_pattern = [re.compile(r'import\s+"(.*?)"')]
        self.include_pattern = [
                    re.compile(r'import\s+"(.*?)"'),
                    re.compile(r'import\s+\(((.|\n)+)\)',flags=re.MULTILINE)
                ]
        self.split_go_import_pattern=re.compile(r'[\n\r \t]+')
        self.import_path_type_list=['dirpath']

    def _extract_imports_with_tree_sitter(self,filepath)->List[List[Text]]:
        cur_file_lang=LangJudge.get_language_of_file(filepath=filepath)
        if not cur_file_lang:
            print(f'ERROR cur_file_lang=None,filepath={filepath}')
            return []
        # print('cur_file_lang=',cur_file_lang)
        parser=self.lang_parse_proxy.get_parser(lang=cur_file_lang)

        import_node_list=extract_imports_with_parser(filepath=filepath,parser=parser)
        # print(f'import_node_list={import_node_list}')
        # includes=[]
        search_part_list=[]
        for import_node_iter in import_node_list:
            node_text_iter=codecs.decode(import_node_iter.text,'utf-8')
            for pattern in self.include_pattern:
                searcher=pattern.search(node_text_iter)
                if searcher:
                    search_part=searcher.group(1)
                    search_part_list.append(search_part)
                    # print(f'search_part=',search_part)
        new_includes=[]
        for search_part_iter in search_part_list:
            parts=self.split_go_import_pattern.split(search_part_iter)
            parts=[part_iter.replace('"','') for part_iter in parts if part_iter]
            # print('parts=',parts)
            # parts=[tuple(part_iter.split('/')) for part_iter in parts]
            parts=[tuple(part_iter.split('/')) for part_iter in parts]
            new_includes.extend(parts)
        new_includes_asc=sorted(list(set(new_includes)),key=lambda x:len(x),reverse=False)
        new_includes_asc=[list(elem) for elem in new_includes_asc]
        # print(f'new_includes_asc={new_includes_asc}')
        return new_includes_asc
    def extract_imports(self,filepath)->List[List[Text]]:
        return self._extract_imports_with_tree_sitter(filepath=filepath)
class ParseTs(ParseBase):
    def __init__(self):
        # super(ParseTs,self).__init__('ts')
        # self.include_pattern = re.compile(r'import\s+"(.*?)"')
        # import {
        #     FieldConf,
        #     Filter,
        #     relationMap,
        #     relationAnd,
        #     relationOr,
        #     } from "./types"
        super(ParseTs,self).__init__(Constants.LANG_TS)
        self.include_pattern = [
                re.compile(r"import .* from '([^']+)'" ,flags=re.MULTILINE),  # import ... from ''
                re.compile(r"import '([^']+)'",flags=re.MULTILINE),  # import ''
                re.compile(r"require\('([^']+)'\)",flags=re.MULTILINE)  # require('')
            ]
        self.import_path_type_list=['filepath']

    def find_filepaths(self,root_dir):
        return self.find_filepaths_no_suffix(root_dir=root_dir)
class ParseJs(ParseBase):
    def __init__(self):
        # super(ParseTs,self).__init__('ts')
        super(ParseJs,self).__init__(Constants.LANG_JS)
        # self.include_pattern = re.compile(r'import\s+"(.*?)"')
        self.include_pattern = [
                re.compile(r"import .* from '([^']+)'"),  # import ... from ''
                re.compile(r"import '([^']+)'"),  # import ''
                re.compile(r"require\('([^']+)'\)")  # require('')
            ]
        self.import_path_type_list=['filepath']
    def find_filepaths(self,root_dir):
        return self.find_filepaths_no_suffix(root_dir=root_dir)


class ParseOtherLangs(ParseBase):
    def __init__(self):
        super(ParseOtherLangs,self).__init__(Constants.LANG_OTHER)
        self.import_path_type_list=['filepath']

    def extract_imports(self,filepath):
        """
            抽取 header里边所有的 includes
        """
        return []


def deal_suffix_list_of_lang_other(parsers):
    """
        静态处理,通过 ParseManager的parser 对 LangJudge 进行赋值处理
    """
    new_lang_suffix_list_dict={}
    other_suffix_list=[]
    for lang_iter,suffix_list_iter in LangJudge.lang_suffix_list_dict.items():
        if lang_iter in parsers.keys():
            new_lang_suffix_list_dict[lang_iter]=suffix_list_iter
        else:
            other_suffix_list.extend(LangJudge.lang_suffix_list_dict[lang_iter])
    new_lang_suffix_list_dict[Constants.LANG_OTHER]=other_suffix_list
    ##更新文件后缀映射， other 替换其他的
    LangJudge.update_lang_suffix_list_dict(part_dict=new_lang_suffix_list_dict)
    LangJudge.suffix_2_lang_dict={v_iter:k for k,v in new_lang_suffix_list_dict.items() for v_iter in v}
    
class ParseManager(object):
    parsers = {
            Constants.LANG_PYTHON: ParsePython(),
            Constants.LANG_CPP: ParseCpp(),
            ##todo del
            Constants.LANG_C: ParseC(),
            Constants.LANG_Go:ParserGo(),
            Constants.LANG_TS:ParseTs(),
            Constants.LANG_JS:ParseJs(),
            Constants.LANG_OTHER:ParseOtherLangs()
        }

    ##对LangJudge的 suffix_2_lang_dict 赋值，根据后缀suffix能找到parser
    deal_suffix_list_of_lang_other(parsers)

    @staticmethod
    def bool_file_match_lang(language,filename):
        if language==Constants.LANG_OTHER:
            pass
        else:
            return LangJudge.bool_file_match_lang(language=self.language,filename=filename)

    @staticmethod
    def supported_parser_languages():
        return list(ParseManager.parsers.keys())

    # @timeit
    @staticmethod
    def create_repo_import_dict(language,project_root):
        """
            每个仓库根据每个语言创建所有的{文件名:路径} 的映射关系
        """
        return ParseManager.parsers[language].create_repo_import_dict(project_root=project_root)

    def create_repo_import_dict_of_language_list(language_list,project_root):
        lang_2_filepath_2_imports_dict={}
        for language_iter in language_list:
            if language_iter in ParseManager.parsers.keys():
                filepath_2_imports_dict=ParseManager.create_repo_import_dict(language=language_iter,project_root=project_root)
                lang_2_filepath_2_imports_dict[language_iter]=filepath_2_imports_dict
        other_filepath_2_imports_dict=ParseManager.create_repo_import_dict(language=Constants.LANG_OTHER,project_root=project_root)
        lang_2_filepath_2_imports_dict.update({Constants.LANG_OTHER:other_filepath_2_imports_dict})
        print(f'**********project_root={project_root}*********')
        for check_k,check_v in lang_2_filepath_2_imports_dict.items():
            print(f'lang={check_k},文件数量={len(check_v)}')
        return lang_2_filepath_2_imports_dict
    


if __name__=='__main__':
    project_root='xxx'

    parse_cpp_obj=ParseCpp()
    cpp_file_2_imports_dict=parse_cpp_obj.create_repo_import_dict(project_root=project_root)
    print('构建成功的引用关系数量',len(cpp_file_2_imports_dict))



