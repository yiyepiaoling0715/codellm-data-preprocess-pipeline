import sys
import os
sys.path.append('..')
sys.path.append('.')
import time
from typing import Generator,List
import numpy as np
import subprocess
import collections
import copy
import faulthandler
import socket
from tree_sitter import Node,Tree
from process_utils.utils import timeit,read_content_with_ignore_error
from process_utils.lang_processor import LangJudge,LangParserProxy
from process_utils.constants import Constants,FileterCounter
from process_utils.path_utils import content_2_lines,split_current_content_by_line
from process_utils.dedup_content import ContentPattern
from process_utils.treesitter_utils import traverse_tree
from repo_graphs.reconstruct import ParsePython


def cause_segfault():  # https://codegolf.stackexchange.com/a/4694/115779
    import ctypes
    ctypes.string_at(0)
def dynamic_find_index_match_chars(source_bytes,start_index_range,dst_chars=['\n']):
    cur_index=start_index_range[0]    
    while cur_index<start_index_range[1]:
        cur_char=source_bytes[cur_index:cur_index+1]
        if cur_char in dst_chars:
            return True,cur_index
        cur_index+=1
    return False,sum(start_index_range)//2

class ExtractNoParserNodeIndo(object):
    def __init__(self):
        self.text_mode=''
    def set_fim_text(self,prefix,suffix,middle):
        self.prefix=prefix
        self.suffix=suffix
        self.middle=middle
        self.text_mode='fim'
    def set_normal_text(self,normal_text):
        self.normal_text=normal_text
        self.text_mode='normal'
    def get_fim_text_tuple(self):
        if self.text_mode=='fim':    
            try:        
                assert len(self.prefix)>5 and len(self.suffix)>5 and len(self.middle)>5,print(f'get_fim_text_tuple self.prefix={self.prefix},self.suffix={self.suffix},self.middle={self.middle}')
            except AssertionError as e:
                print(f'ERROR {e.args}')
            return (self.prefix,self.suffix,self.middle)
        elif self.text_mode=='normal':
            return (self.normal_text,'','')
        else:
            raise ValueError('error')
class ExtractNodeInfo(object):
    # overlap_ratio=1/2
    # window_size=4000
    def __init__(self,node:Node,source_bytes:bytes,overlap_ratio=1/2,prefix_window_size=4000,suffix_window_size=400):
        # (context_start_index,context_end_index)]={'prefix':prefix_part,      'middle':middle_part,'suffix':suffix_part}
        self.node:Node=node
        self.source_bytes=source_bytes
        self.overlap_ratio=overlap_ratio
        self.prefix_window_size=prefix_window_size
        self.suffix_window_size=suffix_window_size
 
        ##todo  match semantically   sibling function
        # context_end_index=node.end_byte+self.suffix_window_size
        bool_changed_end_index,context_end_index=dynamic_find_index_match_chars(
                                source_bytes=source_bytes.decode('utf8',errors='ignore'),
                                start_index_range=[node.end_byte+suffix_window_size-100,node.end_byte+suffix_window_size+100],
                                dst_chars=['\n'])
        
        ##todo,改为与前文有关的
        context_start_index=max(0,node.start_byte-self.prefix_window_size)
        self.middle_arange=[node.start_byte,node.end_byte]
        self.context_arange=[context_start_index,context_end_index]
        self.context_distance=self.context_arange[1]-self.context_arange[0]
        # self.context_arange=(context_start_index,context_end_index)
        # self._set_context_range(context_arange=self.context_arange)
        # self._set_quarter_index_list(context_arange=self.context_arange)
        self._set_fim_text(node=node,source_bytes=source_bytes)


    def _set_fim_text(self,node:Node,source_bytes:bytes):
        middle_part_bytes=source_bytes[node.start_byte:node.end_byte+1]
        prefix_part_bytes=source_bytes[self.context_arange[0]:node.start_byte]
        # suffix_part_bytes=source_bytes[node.end_byte+1:self.context_end_index]
        suffix_part_bytes=source_bytes[node.end_byte+1:self.context_arange[1]+1]
        self.middle_part=middle_part_bytes.decode('utf8',errors='ignore')
        self.prefix_part=prefix_part_bytes.decode('utf8',errors='ignore')
        # print('suffix_part=\n',source_bytes[node.end_byte+1:self.context_end_index])
        self.suffix_part=suffix_part_bytes.decode('utf8',errors='ignore')
        # self.middle_start_byte=node.start_byte
        # self.middle_end_byte=node.end_byte
        assert len(source_bytes[self.context_arange[0]:self.context_arange[1]+1])==len(prefix_part_bytes)+len(middle_part_bytes)+len(suffix_part_bytes)
    
    def reset_fim_text_by_start_index(self,new_context_start_index):
        # self.prefix_part=self.source_bytes[new_context_start_index:self.middle_start_byte].decode('utf8',errors='ignore')
        self.prefix_part=self.source_bytes[new_context_start_index:self.middle_arange[0]].decode('utf8',errors='ignore')
        # self.old_context_start_index=self.context_start_index
        # self.context_start_index=new_context_start_index
        self.context_arange[0]=new_context_start_index
    
    def __repr__(self):
        print_str=f'node={self.node},node.type={self.node.type},\nparent={self.node.parent},\n'+\
            f'named_children={self.node.named_children},\n'+\
            f'parse_state={self.node.parse_state},\ngrammar_name={self.node.grammar_name}\n'+\
            f'context_arange={self.context_arange},\nmiddle_part=\n{self.middle_part}\n*********************************'
            # f'child(0)={child0},\nnamed_child={named_child0},
        return print_str

class CodeFileProcess(object):
    def __init__(self):
        pass
    
    @staticmethod
    def judge_2_node_is_contained(chosen_node:ExtractNodeInfo,relate_node:ExtractNodeInfo):
        """
            return: True 无重叠=>用fim, 
                    False 有重叠=>不使用fim
        """
        assert relate_node.context_arange[1]>relate_node.context_arange[0]
        assert chosen_node.context_arange[1]>chosen_node.context_arange[0]
        
        # return (relate_node.context_end_index<chosen_node.context_start_index or chosen_node.context_end_index<relate_node.context_start_index)
        return (relate_node.middle_arange[1]+1000<chosen_node.middle_arange[0] or chosen_node.middle_arange[1]+1000<relate_node.middle_arange[0])

    @staticmethod
    def pick_part_fim_texts_from_list(node_list:List[ExtractNodeInfo],other_kept_node_list=[],cur_file_lang=None)->List[ExtractNodeInfo]:
        """
            shuffle node, 遍历 node, 确认node之间无overlap, 
            如果没有overlap,加入new_kept_node_list
            return new_kept_node_list,没有overlap的 tree_sitter node list
        """
        node_list_shuffle=np.copy(node_list).tolist()
        np.random.shuffle(node_list_shuffle)
        # node_list_shuffle=node_list
        # visited_node_list=[]
        new_kept_node_list=[]
        while node_list_shuffle:
            chosen_node=node_list_shuffle.pop()
            if not new_kept_node_list and not other_kept_node_list:
                bool_use_fim=True
            else:
                # bool_use_fim=True
                # for visited_node_iter in visited_node_list:
                for kept_node_iter in new_kept_node_list+other_kept_node_list:
                    bool_use_fim=CodeFileProcess.judge_2_node_is_contained(chosen_node=chosen_node,relate_node=kept_node_iter)
                    # print('bool_use_fim=False的chosen_node=',chosen_node)
                    if not bool_use_fim:
                        break
            if bool_use_fim:
                new_kept_node_list.append(chosen_node)
                # [node_iter for node_iter in new_kept_node_list]

        if np.random.random()<0.001:
            print('**********筛选后保留数量kept_node 如下***********')
            for new_kept_node_iter in new_kept_node_list:
                print(new_kept_node_iter)
            print(f'cur_file_lang={cur_file_lang},node_list数量={len(node_list)},other_kept_node_list数量={len(other_kept_node_list)},筛选后保留数量kept_node_list={len(new_kept_node_list)}')
        return new_kept_node_list


class PaserCodeFile(object):
    work_env=os.environ['WORK_ENV']
    lang_parse_proxy=LangParserProxy(work_env=work_env)
    code_file_processor=CodeFileProcess()

    """判断是否保留node"""
    @staticmethod
    def judge_keep_node(node:Node)->bool:
        """
            单多行兼用的过滤node的逻辑判断
        """
        if node.grammar_name in Constants.INTERESTING_TYPE_2_LENGTH_THRES_DICT.keys():
            min_len_thres=Constants.INTERESTING_TYPE_2_LENGTH_THRES_DICT[node.grammar_name].get('min',None)
            if min_len_thres and len(node.text)<min_len_thres:
                return False,f'len(node.text)<{min_len_thres}'
            max_len_thres=Constants.INTERESTING_TYPE_2_LENGTH_THRES_DICT[node.grammar_name].get('max',None)
            if max_len_thres and len(node.text)>max_len_thres:
                return False,f'len(node.text)>{max_len_thres}'
        #comment 无node_children
        # print(node.named_children,node.grammar_name)
        if not node.named_children and node.grammar_name not in ['comment']:
            false_msg='not node.named_children'
            return False,false_msg
        name_children_type_set=set([name_children.type for name_children in node.named_children])
        # if name_children_type_set.intersection(set([
        #     'string_literal',  #cpp
        #     'string','integer','float'   #python
        #     ])):
        if name_children_type_set.intersection(Constants.TREE_SITTER_MIDDLE_IGNORE_TYPES):
            false_msg='name_children_type_set'
            return False,false_msg
        if node.end_byte-node.start_byte>1000:
            false_msg='node.end_byte-node.start_byte>1000'
            return False,false_msg
        if node.end_byte-node.start_byte<5:
            false_msg='node.end_byte-node.start_byte<5'
            return False,false_msg
        return True,'keep'
    @staticmethod
    def base_process_cpp_content(source_bytes,parser,interesting_types,prefix_window_size,suffix_window_size,other_kept_node_list=[],cur_file_lang=None)->List[ExtractNodeInfo]:
        """
            解析source_bytes,根据interesting_types 过滤 不需要node,长短条件过滤node,被包含的node过滤
            随机乱序选择没有overlap的node list
        """
        tree = parser.parse(source_bytes)

        #for check begin
        all_check_node_list=[node for node in traverse_tree(tree)]
        all_check_node_list=[node for node in all_check_node_list  if (1000>node.end_byte-node.start_byte>10) and (node.grammar_name not in Constants.IGNORE_TREE_SITTER_TYPES+Constants.TREE_SITTER_INTERESTING_TYPES_OF_INLINE+Constants.TREE_SITTER_INTERESTING_TYPES_OF_MULTI_LINE)]
        if all_check_node_list and np.random.random()<0.001:
            print('******看下不同grammar具体形态********')
            for check_node_iter in all_check_node_list[:20]:
                print(f'grammar_name={check_node_iter.grammar_name},check_node_text={source_bytes[check_node_iter.start_byte:check_node_iter.end_byte+1]}')
        all_grammar_name_list=[node.grammar_name for node in all_check_node_list]
        grammar_name_2_counter_dict=collections.Counter(all_grammar_name_list)
        for grammar_name_iter,counter_iter in grammar_name_2_counter_dict.items():
            if grammar_name_iter not in FileterCounter.grammar_name_2_counter_dict.keys():
                FileterCounter.grammar_name_2_counter_dict[grammar_name_iter]=0
            FileterCounter.grammar_name_2_counter_dict[grammar_name_iter]+=counter_iter
        # # #for check begin
        # print('**********看下无过滤的原始所有grammar node begin**********')
        # print(f'interesting_types={interesting_types}')
        # all_check_node_list=[node for node in traverse_tree(tree)]
        # # if all_check_node_list and np.random.random()<0.001:
        # if all_check_node_list:
        #     print('******看下不同grammar具体形态********')
        #     for check_node_iter in all_check_node_list:
        #         print(check_node_iter.grammar_name,source_bytes[check_node_iter.start_byte:check_node_iter.end_byte+1])
        # print('**********看下无过滤的原始所有grammar node end**********')
        # # #for check end
        
        # node_names = map(lambda node: (node,node.grammar_name,node.type,node.start_byte,node.named_children,node.text), traverse_tree(tree))
        node_names=filter(lambda node: node.grammar_name in interesting_types, traverse_tree(tree))
        # print(f'过滤后 node_names={list(node_names)}')
        # for index,node_name in enumerate(node_names):
        extra_node_info_obj_list=[]
        for node in node_names:
            bool_keep_node,false_msg=PaserCodeFile.judge_keep_node(node=node)
            if not bool_keep_node:
                # print(f'not bool_keep_node grammar_name={node.grammar_name},node.text={node.text},index diff={node.end_byte-node.start_byte},node.named_children={node.named_children},false_msg={false_msg}')
                # if b'test_canif_testcase_register' in node.text:
                #     print(f'not keep node.grammar_name={node.grammar_name},node.text={node.text},index diff={node.end_byte-node.start_byte},node.named_children={node.named_children},false_msg={false_msg}')
                continue
            # print(f'kept node.grammar_name={node.grammar_name},node.text={node.text}')
            extra_node_info_obj=ExtractNodeInfo(node=node,source_bytes=source_bytes,
                        prefix_window_size=prefix_window_size,suffix_window_size=suffix_window_size)
            extra_node_info_obj_list.append(extra_node_info_obj)
            # print('extra_node_info_obj=',extra_node_info_obj)
        
        # print('*********extra_node_info_obj_list***********')
        # for extra_node_info_obj_iter in extra_node_info_obj_list:
        #     print(extra_node_info_obj_iter)
        #     print('-------extra_node_info_obj_iter---------')


        kept_node_list=PaserCodeFile.code_file_processor.pick_part_fim_texts_from_list(
                                                                node_list=extra_node_info_obj_list,
                                                                other_kept_node_list=other_kept_node_list,
                                                                cur_file_lang=cur_file_lang)
        if np.random.random()<0.001:
            print('******************kept_node_list******************')
            for kept_node_iter in kept_node_list:
                print('kept_node_iter=\t',kept_node_iter)
                print('-------kept_node_iter-----')
        return kept_node_list

    @staticmethod
    def base_process_cpp_file(file_path,parser,interesting_types,prefix_window_size,suffix_window_size,other_kept_node_list=[],cur_file_lang=None)->List[ExtractNodeInfo]:
        with open(file_path, 'rb') as file:
            source_bytes = file.read()
            # print('source_bytes=\n',bytes(source_bytes,'utf8'))
            kept_node_list=PaserCodeFile.base_process_cpp_content(
                            source_bytes=source_bytes,parser=parser,interesting_types=interesting_types,
                            prefix_window_size=prefix_window_size,suffix_window_size=suffix_window_size,
                            other_kept_node_list=other_kept_node_list,cur_file_lang=cur_file_lang)
            return kept_node_list

    
    @staticmethod
    def process_cpp_file_of_inline(file_path,parser,other_kept_node_list,cur_file_lang)->List[ExtractNodeInfo]:
        # interesting_types = ['function_call','argument_list','parameter_list','binary_expression',# 'unary_expression'  一元表达式]
        interesting_types=Constants.TREE_SITTER_INTERESTING_TYPES_OF_INLINE
        prefix_window_size=Constants.PREFIX_WINDOW_SIZE_OF_INLINE
        suffix_window_size=Constants.SUFFIX_WINDOW_SIZE_OF_INLINE
        kept_node_list=PaserCodeFile.base_process_cpp_file(file_path=file_path,parser=parser,
                            interesting_types=interesting_types,
                            prefix_window_size=prefix_window_size,
                            suffix_window_size=suffix_window_size,
                            other_kept_node_list=other_kept_node_list,
                            cur_file_lang=cur_file_lang)
        return kept_node_list
    
    @staticmethod
    def process_cpp_file_of_multiline(file_path,parser,cur_file_lang)->List[ExtractNodeInfo]:
        # interesting_types = ['function_definition', 'for_statement', 'while_statement', 'if_statement',
        #     'enum_specifier','switch_statement','struct_specifier']        
        interesting_types=Constants.TREE_SITTER_INTERESTING_TYPES_OF_MULTI_LINE
        prefix_window_size=Constants.PREFIX_WINDOW_SIZE_OF_MULTI_LINE
        suffix_window_size=Constants.SUFFIX_WINDOW_SIZE_OF_MULTI_LINE

        kept_node_list=PaserCodeFile.base_process_cpp_file(file_path=file_path,parser=parser,
                    interesting_types=interesting_types,
                    prefix_window_size=prefix_window_size,suffix_window_size=suffix_window_size,cur_file_lang=cur_file_lang)
        return kept_node_list

    @staticmethod
    def use_fim_process_file(file_path)->List[ExtractNodeInfo]:
        cur_file_lang=LangJudge.get_language_of_file(filepath=file_path)
        if not cur_file_lang:
            print(f'ERROR cur_file_lang=None,file_path={file_path}')
            return None
        # print('cur_file_lang=',cur_file_lang)
        parser=PaserCodeFile.lang_parse_proxy.get_parser(lang=cur_file_lang)
        kept_node_list_from_multiline=PaserCodeFile.process_cpp_file_of_multiline(file_path=file_path,parser=parser,cur_file_lang=cur_file_lang)
        # print(f'kept_node_list_from_multiline={kept_node_list_from_multiline}')
        kept_node_list_from_inline=PaserCodeFile.process_cpp_file_of_inline(
                file_path=file_path, parser=parser,other_kept_node_list=kept_node_list_from_multiline,
                cur_file_lang=cur_file_lang)
        # print(f'kept_node_list_from_inline={kept_node_list_from_inline}')
        kept_node_list:List[ExtractNodeInfo]=kept_node_list_from_inline+kept_node_list_from_multiline
        if not kept_node_list and np.random.random()<0.01:
            print(f'use_fim_process_file 解析kept_node_list为空 file_path={file_path} ')
            return None

        kept_node_list_asc_by_start_index=sorted(kept_node_list,key=lambda extra_node_info_obj: extra_node_info_obj.middle_arange[0],reverse=False)
        
        #todo 根据最新排序的node，拓展 prefix，suffix,将文件串联起来
        for index_kept_node in range(1,len(kept_node_list_asc_by_start_index)):
            pre_kept_node=kept_node_list_asc_by_start_index[index_kept_node-1]
            cur_kept_node=kept_node_list_asc_by_start_index[index_kept_node]            
            # if pre_kept_node.context_end_index<cur_kept_node.context_start_index:
            if pre_kept_node.context_arange[1]<cur_kept_node.context_arange[0]:
                new_context_start_index=pre_kept_node.context_arange[1]+1
                # cur_kept_node.prefix_part=cur_kept_node.source_bytes[new_context_start_index:cur_kept_node.middle_start_byte]
                cur_kept_node.reset_fim_text_by_start_index(new_context_start_index=new_context_start_index)
                assert new_context_start_index<cur_kept_node.middle_arange[0]
            elif pre_kept_node.context_arange[1]==cur_kept_node.context_arange[0]:
                print(f'node 初始状态就衔接了 pre_kept_node.context_arange={pre_kept_node.context_arange},cur_kept_node={cur_kept_node}')
            else:
                
                error_msg=f'pre_kept_node.context_arange={pre_kept_node.context_arange} 必须小于 cur_kept_node.context_arange={cur_kept_node.context_arange},pre_kept_node.middle_arange={pre_kept_node.middle_arange},cur_kept_node.middle_arange={cur_kept_node.middle_arange}'
                if np.random.random()<0.0001:
                    print(error_msg)
                    print(f'修改后的context_arange={cur_kept_node.context_arange}')
                new_context_start_index=pre_kept_node.context_arange[1]+1
                cur_kept_node.reset_fim_text_by_start_index(new_context_start_index=new_context_start_index)
                assert new_context_start_index<cur_kept_node.middle_arange[0]
        start_end_index_tuple_list=[(kept_node.context_arange,kept_node.middle_arange) for kept_node in kept_node_list_asc_by_start_index]
        if np.random.random()<0.0001:
            print('reset以后的start_end_index_tuple_list=',start_end_index_tuple_list)
            try:
                if start_end_index_tuple_list[-1][0][0]>5000000:
                    print(f'start_byte过大的file_path={file_path}')
            except Exception as e:
                print(f'ERROR start_end_index_tuple_list {e.args}')
            for start_end_tuple_iter in start_end_index_tuple_list:
                assert (start_end_tuple_iter[0][1]-start_end_tuple_iter[0][0])<10000
                assert (start_end_tuple_iter[1][1]-start_end_tuple_iter[1][0])<1000
        return kept_node_list_asc_by_start_index

    @staticmethod
    def use_fim_parse_repo(repo_dirpath,work_env):
        parse_python_obj=ParsePython()
        filter_filepaths,filanme_2_paths_dict=parse_python_obj.find_filepaths(root_dir=repo_dirpath)
        print('filter_filepaths 数量=',len(filter_filepaths))
        for file_path in filter_filepaths:
            use_fim_process_file(file_path=file_path,work_env=work_env)

    @staticmethod
    def get_all_grammars(self,source_bytes):
        # node_names=filter(lambda node: node.grammar_name in interesting_types,nodes=traverse_tree(tree))
       
        tree = parser.parse(source_bytes)
        nodes=traverse_tree(tree)
        node_names=[node.grammar_name for node in nodes]

class MockParserCodeFile(object):
    window_size_list=[2000,3000,4000]
    def __init__(self):
        pass
    @staticmethod
    def use_fim_in_window_block(lines,debug_node=None):
        
        bool_fim_success=False
        try:
            assert len(lines)>Constants.FIM_LINES_NUM_THRES
        except AssertionError as e:
            if debug_node:
                print(f'debug_node.filepath={debug_node.filepath}')
            print(f'lines数量<{Constants.FIM_LINES_NUM_THRES},check下 \n{lines}')
            lens=[len(line) for line  in lines]
            raise ValueError(f'error len(lines)={len(lines)},max_line_num={max(lens)}')
        prefix=''
        suffix=''
        middle=''
        lines_num=len(lines)
        line_length_list=[len(line) for line in lines]
        def find_max_line_index():
            # max_line_length=max(line_length_list[5:])
            # max_line_index=line_length_list[5:].index(max_line_length)+5
            line_index_list=list(range(lines_num))
            index_length_tuple_list=list(zip(line_index_list,line_length_list))
            index_length_tuple_list.sort(key=lambda tuple_item: tuple_item[1],reverse=True)
            for index_length_tuple_iter in index_length_tuple_list:
                if index_length_tuple_iter[0]<5:
                    continue
                if Constants.FILEPATH_FLAG in lines[index_length_tuple_iter[0]]:
                    continue
                if index_length_tuple_iter[0]>lines_num-2:
                    continue
                return index_length_tuple_iter
            raise ValueError(f'find_max_line_index error,Glines={lines},lines_num={lines_num},index_length_tuple_list={index_length_tuple_list}')
        max_line_index,max_line_length=find_max_line_index()
        skip_line_num=np.random.choice((lines_num//5,lines_num//2))
        # for index_line,line in enumerate(lines[::-1]):
        debug_reason_counter=[]
        for index_line,line in enumerate(lines):
            if index_line<lines_num-1:
                assert line.endswith('\n'),print(f'line=\n{line}行结束')
            if index_line<skip_line_num:
                debug_reason_counter.append('index_line<skip_line_num')
                continue
            if ContentPattern.print_pattern.search(line):
                debug_reason_counter.append('print_pattern')
                continue
            if len(line)<min(30,max_line_length//2):
                debug_reason_counter.append('len(line)<min')
                continue
            bool_fim_success=True
            if np.random.random()<0.0001:
                print(f'break index_line={index_line},len(lines)={len(lines)}')
            break
        
        if index_line>=lines_num-5:
            middle_index_line=max_line_index
        elif bool_fim_success:
            middle_index_line=index_line
        else:
            print('bool_fim_success=False lines=\n',lines)
            raise ValueError(f'error lines数量={len(lines)},随机选的skip_line_num={skip_line_num},退出时候的index_line={index_line}\ndebug_reason_counter={debug_reason_counter[-15:]}')
        prefix=''.join(lines[:middle_index_line])
        suffix=''.join(lines[middle_index_line+1:])
        middle=lines[middle_index_line]
        try:
            assert len(prefix+suffix+middle)==len(''.join(lines)),print(f"len(prefix+suffix+middle)={len(prefix+suffix+middle)},join(lines)={len(''.join(lines))}")
            assert len(prefix)>5 and len(suffix)>5 and len(middle)>5,print(f'use_fim_in_window_block prefix={prefix},suffix={suffix},middle={middle},退出时候的index_line={index_line}\n,lines数量={len(lines)},max_line_index={max_line_index},debug_reason_counter={debug_reason_counter[-15:]}')
        except AssertionError as e:
            print(f'AssertionError={e.args}')
        return prefix,suffix,middle
            
    def use_fim_process_file(self,content,debug_node=None):
        # content=read_content_with_ignore_error(filepath=file_path)
        window_size=np.random.choice(MockParserCodeFile.window_size_list)
        new_content_iter_slices,split_lines_list=split_current_content_by_line(content_window_size=window_size,current_context=content)
        extract_no_parse_node_info_obj_list=[]
        for index_lines,lines_iter in enumerate(split_lines_list):
            try:
                len(lines_iter)
            except TypeError as e:
                print(f'use_fim_process_file content={content}')
                print(f'use_fim_process_file split_lines_list={split_lines_list}')
                print(f'use_fim_process_file lines_iter={lines_iter}')
                raise ValueError(f'error use_fim_process_file window_size={window_size},len(content)={len(content)}')
            if len(lines_iter)<=Constants.FIM_LINES_NUM_THRES:
                new_content_iter=new_content_iter_slices[index_lines]
                extract_no_parse_node_info_obj=ExtractNoParserNodeIndo()
                extract_no_parse_node_info_obj.set_normal_text(normal_text=new_content_iter)
            else:
                prefix,suffix,middle=self.use_fim_in_window_block(lines=lines_iter,debug_node=debug_node)
                extract_no_parse_node_info_obj=ExtractNoParserNodeIndo()
                extract_no_parse_node_info_obj.set_fim_text(prefix=prefix,suffix=suffix,middle=middle)
            extract_no_parse_node_info_obj_list.append(extract_no_parse_node_info_obj)
        return extract_no_parse_node_info_obj_list

if __name__=='__main__':
    # lang='python'
    # work_env='xxx'
    if socket.gethostbyname(socket.gethostname())=='xxx':
        file_path='xxx'
        repo_dirpath='xxx'
        os.environ['WORK_ENV']='local'
    else:
        os.environ['WORK_ENV']='xxx'
    print(socket.gethostbyname(socket.gethostname()))
    new_kept_node_list=use_fim_process_file(file_path=file_path)

    print('**********筛选后保留数量kept_node 如下***********')
    for new_kept_node_iter in new_kept_node_list:
        print(new_kept_node_iter)
    print(f'node_list数量={len(new_kept_node_list)}')
    
    # use_fim_parse_repo(repo_dirpath=repo_dirpath,work_env=work_env)

