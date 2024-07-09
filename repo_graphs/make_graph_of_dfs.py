from typing import List,Dict,Text
import copy
import os
from collections import defaultdict,Counter
from process_utils.utils import timeit,concat_path_and_content
import math
import numpy as np
from process_utils.utils import read_content_with_ignore_error
from process_utils.dedup_content import DeDupSpan
from process_utils.dedup_content_func import clean_cross_line_of_content
from process_utils.lang_processor import LangJudge
from process_utils.path_utils import split_current_content_by_line

class  PathNode(object):
    def __init__(self):
        self.language=''
        self.no_changed_language=''
        self.filepath=''
        self.content=''
        self.in_nodes=[]
        self.out_nodes=[]
        self.in_nodes_counter=0
        self.out_nodes_counter=0
    def add_in_nodes(self,path_nodes):
        for path_node in path_nodes:        
            self.in_nodes.append(path_node)
    def add_out_node(self,path_nodes):
        for path_node in path_nodes:        
            self.out_nodes.append(path_node)
    def __repr__(self):
        suffix_filepath='/'.join(self.filepath.split('/')[-5:])
        return f'{suffix_filepath} in_nodes:{len(self.in_nodes)} out_nodes:{len(self.out_nodes)}'
    
    def _read_content(self,filepath):
        content=read_content_with_ignore_error(filepath=filepath)

        if np.random.random()<0.9:
            pass
        return content
        
    def read_content(self):
        """
            外部加整体的path
        """
        if self.content:
            return self.content
        if os.path.isfile(self.filepath):
           content=self._read_content(filepath=self.filepath)
        #todo 去掉,只保留一个文件
        elif os.path.isdir(self.filepath):
            raise ValueError(f'error 必须为filepath,非目录路径 {self.filepath}')
            #内部的，所以要+path
            content=''
            files=os.listdir(self.filepath)
            suffixes=[file.split('.')[-1] for file in files]
            top1_suffix_counter_tuple=sorted(Counter(suffixes).items(),key=lambda x:x[1],reverse=True)
            top1_suffix=top1_suffix_counter_tuple[0][0]
            filter_files=[file for file in files if file.endswith(top1_suffix)]
            counter_read=0
            for file_iter in files:
                filepath_iter=os.path.join(self.filepath,file_iter)
                if not os.path.isfile(filepath_iter):
                    continue
                content_iter=self._read_content(filepath=filepath_iter)
                if content_iter:
                    new_content_iter=concat_path_and_content(filepath=filepath_iter,content=content_iter)
                    content+=new_content_iter
                    counter_read+=1
                if counter_read>10:
                    break
        else:
            raise ValueError('error')

        self.content=content
        return content

class PathGraph(object):
    """
        图结构， node in node out
    """
    def __init__(self,vertices):
        """
            vertices: 顶点数
        """
        self.graph = defaultdict(list)
        self.V=vertices
        self.node_2_index_dict={}
        self.index_2_node_dict={}

    def add_node_2_index(self,filepath_2_node_dict:Dict):
        index=0
        for filepath_iter, node_iter in filepath_2_node_dict.items():
            self.node_2_index_dict[node_iter]=index
            self.index_2_node_dict[index]=node_iter
            index+=1

    def add_edge(self,path_node_obj):
        for in_node_iter in path_node_obj.in_nodes:
            self.graph[path_node_obj].append(in_node_iter)
    
    def topological_sort_util_by_dfs(self,cur_node,visited,stack):
        visited[self.node_2_index_dict[cur_node]]=True
        for in_node_iter in self.graph[cur_node]:
            if visited[self.node_2_index_dict[in_node_iter]]==False:
                self.topological_sort_util_by_dfs(in_node_iter,visited,stack)
        stack.insert(0,cur_node)

    def topological_sort_by_dfs(self)->List[PathNode]:
        assert self.V==len(self.node_2_index_dict)
        visited=[False]*self.V
        stack=[]
        for i in range(self.V):
            if visited[i]==False:
                self.topological_sort_util_by_dfs(self.index_2_node_dict[i],visited,stack)
        # print(stack)
        # print('visited',visited)
        return stack

def create_tree(file_2_imported_files_dict,language):
    """
        根据 file:imported_files 的dict 创建树,每个file都是个node,
        根据node_in,node_out 创建节点之间的关系
    """
    add_node_counter=0
    filepath_2_node_dict={}
    ##所有的路径都构建 PathNode 对象
    for file_iter,imported_files_dict_iter in file_2_imported_files_dict.items():
        if file_iter not in filepath_2_node_dict.keys():
            center_path_node_obj=PathNode()
            center_path_node_obj.language=language
            center_path_node_obj.no_changed_language=LangJudge.get_no_change_language_of_file(file_path=file_iter)
            # LangJudge.suffix_2_lang_dict_no_changed
            center_path_node_obj.filepath=file_iter
            filepath_2_node_dict[file_iter]=center_path_node_obj
            add_node_counter+=1
        else:
            center_path_node_obj=filepath_2_node_dict[file_iter]
        for partial_import_iter,import_filepath_list_iter in imported_files_dict_iter.items():
            # try:
            assert isinstance(import_filepath_list_iter,list)
            # except AssertionError as e:
            #     err_smg=f'import_filepath非string,import_filepath={import_filepath}'
            #     raise ValueError(err_smg)
            for import_filepath in import_filepath_list_iter:
                assert os.path.isfile(import_filepath)
                if import_filepath not in filepath_2_node_dict.keys():
                    in_path_node_obj=PathNode()
                    in_path_node_obj.language=language
                    in_path_node_obj.no_changed_language=LangJudge.get_no_change_language_of_file(file_path=file_iter)
                    in_path_node_obj.filepath=import_filepath
                    filepath_2_node_dict[import_filepath]=in_path_node_obj
                    add_node_counter+=1
                else:
                    in_path_node_obj=filepath_2_node_dict[import_filepath]
                    assert in_path_node_obj.language 
                    assert in_path_node_obj.filepath
                center_path_node_obj.add_in_nodes([in_path_node_obj])
                in_path_node_obj.add_out_node([center_path_node_obj])
    print(f'共创建filepath_2_node_dict节点数量={len(filepath_2_node_dict)},add_node_counter={add_node_counter},2者应该相同')
    return filepath_2_node_dict

def calc_counter(filepath_2_node_dict):
    for filepath_iter,path_node_obj in filepath_2_node_dict.items():
        path_node_obj.in_nodes_counter=len(path_node_obj.in_nodes)
        path_node_obj.out_nodes_counter=len(path_node_obj.out_nodes)

def dfs_visit_graph(node,filepath_2_node_dict_of_group:Dict)->Dict[Text,PathNode]:
    """
        将每个文件和PathNode建立关联,node 根据 in/out关系完善import相关的文件路径
        return: 所有能构建同一个图的 {filepath:pathnode}
    """
    in_nodes=node.in_nodes
    out_nodes=node.out_nodes
    filepath_2_node_dict_of_group[node.filepath]=node
    for in_node in in_nodes:
        if in_node.filepath not in filepath_2_node_dict_of_group.keys():
            filepath_2_node_dict_of_group[in_node.filepath]=in_node
            dfs_visit_graph(in_node,filepath_2_node_dict_of_group)
    for out_node in out_nodes:
        if out_node.filepath not in filepath_2_node_dict_of_group.keys():
            filepath_2_node_dict_of_group[out_node.filepath]=out_node
            dfs_visit_graph(out_node,filepath_2_node_dict_of_group)
    return filepath_2_node_dict_of_group

def dfs_split_by_edge(filepath_2_node_dict:Dict[str,PathNode])->List[Dict[str,PathNode]]:
    filepath_2_node_dict_num_record=len(filepath_2_node_dict.keys())
    """
       将一个仓库内构建的  filepath_2_node_dict 按照group分组后 构件图,然后加入List
    """
    filepath_2_node_dict_of_group_list:List[Dict[str,PathNode]]=[]
    while len(filepath_2_node_dict.keys())>0:
        # print(f'len(filepath_2_node_dict.keys())={len(filepath_2_node_dict.keys())}')
        filepath_iter,node_iter=filepath_2_node_dict.popitem()
        try:
            filepath_2_node_dict_of_group_iter=dfs_visit_graph(node_iter,{})
        except RecursionError as e:
            error_info=f'RecursionErrorfilepath_iter={filepath_iter},node_iter={node_iter}'
            continue
        if not filepath_2_node_dict_of_group_iter:
            print('node为空,无法构件图,node=',node_iter)
            continue

        filepath_2_node_dict_of_group_list.append(filepath_2_node_dict_of_group_iter)
        ##构建局部图以后,从整体的filepath_2_node_dict remove
        for filepath_iter,node_iter in filepath_2_node_dict_of_group_iter.items():
            if filepath_iter in filepath_2_node_dict.keys():
                filepath_2_node_dict.pop(filepath_iter)
    
    filepath_2_node_dict_of_group_num_list=[len(check_group_iter) for check_group_iter in filepath_2_node_dict_of_group_list]
    filepath_2_node_dict_of_group_num_inall=sum(filepath_2_node_dict_of_group_num_list)
    print(f'filepath_2_node_dict初始数量={filepath_2_node_dict_num_record},\n dfs_split_by_edge 后数量减少为{len(filepath_2_node_dict)}(0是合理的,说明全加工了),\n 其中用来加工分组的filepath_2_node_dict_of_group_list数量={filepath_2_node_dict_of_group_num_inall}')
    return filepath_2_node_dict_of_group_list

def sort_by_in_nodes_counter(filepath_2_node_dict_of_group_list:List[Dict[str,PathNode]]):
    """
        文件引用多的在后,被引用的在前,
        每个图内如此,仓库内的图也是如此
    """
    grouped_nodes_by_asc_list:List[List]=[]
    for filepath_2_node_dict_of_group_iter in filepath_2_node_dict_of_group_list:
        grouped_nodes_by_asc=sorted(list(filepath_2_node_dict_of_group_iter.values()),key=lambda node:node.in_nodes_counter,reverse=False)
        grouped_nodes_by_asc_list.append(grouped_nodes_by_asc)
    #imported多的文件在后
    grouped_nodes_by_asc_list_sorted=sorted(grouped_nodes_by_asc_list,key=lambda grouped_nodes_by_asc:grouped_nodes_by_asc[-1].in_nodes_counter,reverse=False)
    assert len(grouped_nodes_by_asc_list_sorted)>0
    try:
        # assert grouped_nodes_by_asc_list_sorted[-1].in_nodes_counter>=grouped_nodes_by_asc_list_sorted[0].in_nodes_counter
        assert grouped_nodes_by_asc_list_sorted[-1][-1].in_nodes_counter>=grouped_nodes_by_asc_list_sorted[0][0].in_nodes_counter
    except AttributeError as e:
        print(f'len(grouped_nodes_by_asc_list_sorted)={len(grouped_nodes_by_asc_list_sorted)},grouped_nodes_by_asc_list_sorted[-1]={grouped_nodes_by_asc_list_sorted[-1]},grouped_nodes_by_asc_list_sorted[0]={grouped_nodes_by_asc_list_sorted[0]}')
        raise ValueError('AttributeError')
    grouped_nodes_by_asc_dict_sorted=[{node_iter.filepath:node_iter for node_iter in list_iter} for list_iter in grouped_nodes_by_asc_list_sorted]

    return grouped_nodes_by_asc_list_sorted,grouped_nodes_by_asc_dict_sorted

def sort_by_graph(filepath_2_node_dict_of_group_list:List[Dict[str,PathNode]]):    
    """
        根据文件路径分组的列表，对其进行排序
        return:  List[group node list], List[group filepaths]
    """
    stack_list:List[List[PathNode]]=[]
    filepaths_list:List[List[str]]=[]
    stack_filepath_tuple_list=[]
    #将 group后的 filepath/node 建立关联关系,拓扑图排序
    for filepath_2_node_dict_of_group_iter in filepath_2_node_dict_of_group_list:
        path_graph_obj_iter=PathGraph(vertices=len(filepath_2_node_dict_of_group_iter)) 
        path_graph_obj_iter.add_node_2_index(filepath_2_node_dict=filepath_2_node_dict_of_group_iter)
        for filepath_iter,node_iter in filepath_2_node_dict_of_group_iter.items():
            path_graph_obj_iter.add_edge(node_iter)
        stack_iter:List[PathNode]=path_graph_obj_iter.topological_sort_by_dfs()
        stack_iter=stack_iter[::-1]
        # print(stack_iter)
        #拓扑图构建后,按照依赖关系重排序, 被依赖在前,依赖在后
        stack_list.append(stack_iter)
        filepath_of_stack_iter=[node_iter.filepath for node_iter in stack_iter]
        ##todo ??
        # filepaths_list.append(list(filepath_2_node_dict_of_group_iter.keys()))
        # filepaths_list.append(filepath_of_stack_iter)
        stack_filepath_tuple_list.append([stack_iter,filepath_of_stack_iter])
        # for node_iter in stack_iter[::-1]:
        #     print('node_iter=',node_iter)
        # print('*********************************************')
    
    ##根据拓扑图节点数量对group进行排序,节点少的在前
    # stack_list_asc_by_stack_num=sorted(stack_list,key=lambda x:len(x),reverse=False)
    stack_filepath_tuple_list_asc_by_stack_num=sorted(stack_filepath_tuple_list,key=lambda x:len(x[0]),reverse=False)
    stack_list_asc_by_stack_num=[elem[0] for elem in stack_filepath_tuple_list_asc_by_stack_num]
    filepaths_list_asc_by_stack_num=[elem[1] for elem in stack_filepath_tuple_list_asc_by_stack_num]
    asc_stack_num_list=[len(check_elem) for check_elem in stack_list_asc_by_stack_num]
    print(f'head少,tail多是合理的  asc_stack_num_list head 10={asc_stack_num_list[:10]},tail 10={asc_stack_num_list[-10:]}')
    if len(asc_stack_num_list)>0:
        assert asc_stack_num_list[0]<=asc_stack_num_list[-1]
        for stack,filepaths in zip(stack_list_asc_by_stack_num,filepaths_list_asc_by_stack_num):
            if len(stack)==1 and np.random.random()<0.001:
                print('stack num==1 filepath=',stack[0].filepath)
            for node_iter,filepath_iter in zip(stack,filepaths):
                assert node_iter.filepath==filepath_iter

    return stack_list_asc_by_stack_num,filepaths_list_asc_by_stack_num



@timeit
def make_graph_process_of_language(file_2_imported_files_dict,language):
    """
        依赖关系， n:m,  n数量>m数量
    """
    for check_filepath,imported_files_iter in file_2_imported_files_dict.items():
        if 'teds-http-test.cpp' in check_filepath:
            print(f'file_2_imported_files_dict teds-http-test.cpp={check_filepath}',imported_files_iter)

    filepath_2_node_dict=create_tree(file_2_imported_files_dict=file_2_imported_files_dict,language=language)
    # for check_filepath,node_iter in filepath_2_node_dict.items():
    #     if 'teds-http-test.cpp' in check_filepath:
    #         print(f'filepath_2_node_dict teds-http-test.cpp={check_filepath}',node_iter)
    calc_counter(filepath_2_node_dict)    
    filepath_2_node_dict_of_group_list=dfs_split_by_edge(filepath_2_node_dict=filepath_2_node_dict)
    grouped_nodes_by_asc_list,grouped_nodes_by_asc_dict_sorted=sort_by_in_nodes_counter(filepath_2_node_dict_of_group_list=filepath_2_node_dict_of_group_list)
    # grouped_nodes_by_asc_list=sort_by_graph(filepath_2_node_dict_of_group_list=filepath_2_node_dict_of_group_list)
    stack_list,filepaths_list=sort_by_graph(filepath_2_node_dict_of_group_list=grouped_nodes_by_asc_dict_sorted)
    return stack_list,filepaths_list

def make_graph_process_of_languages(lang_2_file_2_imported_files_dict):
    """
        将一个仓库 根据语言分别构建的 文件依赖map：lang_2_file_2_imported_files_dict,
        创建 node 堆栈后,返回
    """
    stack_list_all:List[List[PathNode]]=[]
    filepaths_list_all:List[List[str]]=[]
    language_list:List[Text]=[]
    for lang_iter,file_2_imported_files_dict_iter in lang_2_file_2_imported_files_dict.items():
        # print('lang_iter=',lang_iter)
        stack_list_iter,filepaths_list_iter=make_graph_process_of_language(file_2_imported_files_dict=file_2_imported_files_dict_iter,language=lang_iter)
        #语言粒度对 group node list 进行排序
        ##todo 语言维度打乱, 混合排序 训练
        stack_list_all+=stack_list_iter
        filepaths_list_all+=filepaths_list_iter
        language_list.extend([lang_iter]*len(stack_list_iter))
    if len(stack_list_all)>0 and stack_list_all[-1]>100:
        print(f'stack_list_all[-1]>100,stack_list_all[-10:]={stack_list_all[-10:]},language={set(language_list[-10:])}')
    return stack_list_all,filepaths_list_all,language_list
    


if __name__=='__main__':
    pass
