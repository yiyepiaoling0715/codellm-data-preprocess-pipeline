import os
from typing import Dict,List,Text
import numpy as np
from process_utils.utils import timeit,concat_path_and_content
from process_utils.dedup_content import DeDupSpan
from process_utils.dedup_content_func import clean_cross_line_of_content
from repo_graphs.attributes.calc_lens import calc_val_about_len_columns
from repo_graphs.fim_parse import PaserCodeFile
from process_utils.common_utils import FIMProxy
from process_utils.path_utils import split_current_content_by_line
from repo_graphs.fim_parse import MockParserCodeFile
from repo_graphs.make_graph_of_dfs import PathNode
from process_utils.constants import FileterCounter


def _process_pathnode(node_iter:PathNode):
    """
        处理PathNode content, 根据 统计指标进行过滤,是否保留content，截断lines
        所有的对文件内容的处理都应该在这个之后,比如 fim
        组合 content+path
    """
    content_iter=node_iter.read_content()
    if not content_iter:
        FileterCounter.file_read_content_error+=1
        return False,None
        print(node_iter.filepath,'未找到文件内容')
    """
        'avg_line_length':int(avg_line_length),
        'max_line_length':int(max_line_length),
        'alphanum_ratio':round(alphanum_ratio,5),
        'size':size,
        'comments_ratio':round(comments_ratio,5)
    """
    # len_val_dict=calc_val_about_len_columns(content=content_iter,language=node_iter.language)
    len_val_dict=calc_val_about_len_columns(content=content_iter,language=node_iter.no_changed_language)
    alphanum_ratio=len_val_dict['alphanum_ratio']
    lines_num=len_val_dict['lines_num']
    avg_line_length=len_val_dict['avg_line_length']
    max_line_length=len_val_dict['max_line_length']
    comments_ratio=len_val_dict['comments_ratio']
    top5_word_counter=len_val_dict['top5_word_counter']
    lines=len_val_dict['lines']
    # #for check  
    # if 'iconfont.css' in node_iter.filepath:
    #     print(f'check iconfont.css details\n{node_iter.filepath}  max_line_length={max_line_length} lines_num={lines_num} alphanum_ratio={alphanum_ratio} comments_ratio={comments_ratio}\nlines={lines}lines结束')
    # if max_line_length>1000 and line_number<10:
    if max_line_length>1000:
        FileterCounter.line_max_line_length+=1
        FileterCounter.line_max_line_length_token_num+=len(content_iter)
        if np.random.random()<0.001:
            print(f'过滤掉line_max_line_length={max_line_length},node_iter.filepath={node_iter.filepath}')
        return False,None
    if avg_line_length<5:
        FileterCounter.line_avg_line_length+=1
        FileterCounter.line_avg_line_length_token_num+=len(content_iter)
        if np.random.random()<0.01:
            print(f'过滤掉line_avg_line_length={line_avg_line_length},node_iter.filepath={node_iter.filepath}')
        return False,None
    if alphanum_ratio>float(os.environ['alphanum_ratio']):
        FileterCounter.file_alphanum_ratio+=1
        FileterCounter.file_alphanum_ratio_token_num+=len(content_iter)
        if np.random.random()<0.1:
            print(f'过滤掉alphanum_ratio={alphanum_ratio},node_iter.filepath={node_iter.filepath}')
        return False,None
    # if comments_ratio<float(os.environ['comments_ratio']):
    #     FileterCounter.file_comments_ratio+=1
    #     print(f'过滤掉comments_ratio={comments_ratio},node_iter.filepath={node_iter.filepath}')
    #     return False,None
    lines_after_dedup=clean_cross_line_of_content(lines=lines,filepath=node_iter.filepath)
    if not lines_after_dedup:
        FileterCounter.file_clean_cross_line+=1
        FileterCounter.file_clean_cross_line_token_num+=len(content_iter)
        print(f'lines_after_dedup 过滤掉为空,node_iter.filepath={node_iter.filepath}')
        return False,None
    FileterCounter.file_clean_cross_line_token_num+=(len(content_iter)-len(lines_after_dedup))
    #最大行数量  ##todo 过滤??
    max_line_number=int(os.environ['max_line_number'])
    if lines_num>max_line_number:
        FileterCounter.line_max_line_number+=1
        FileterCounter.line_max_line_number_token_num+=len(content_iter)
        print(f'过滤掉line_number={lines_num},node_iter.filepath={node_iter.filepath}')
    content_of_trunc=''.join(lines_after_dedup[:max_line_number])
    #内容合并path
    assert isinstance(node_iter.filepath,str) and not ';' in node_iter.filepath
    new_content_iter=concat_path_and_content(filepath=node_iter.filepath,content=content_of_trunc)
    return True,new_content_iter

def process_pathnode_with_fim(node:PathNode,source='single_file',bool_fim=False)->Dict:
    """
        核心处理逻辑,所有的文件处理都归到此函数
        常规处理
            语言 无parse支持        
            0.1比例
        fim 处理
            语言有parser支持
            0.9
        line 处理 单行,行内切分
    """
    ## new_content_iter  各种规则清洗过滤后的
    bool_content,new_content_iter=_process_pathnode(node_iter=node)
    if not bool_content:
        ## _process_pathnode 已经统计过,此处不做统计
        return False,None
    if not bool_fim:
        FileterCounter.file_fim_false+=1
        return True,{'new_content':new_content_iter}
    if source=='single_file':
        fim_false_thres=0.1
    elif source=='stack':
        fim_false_thres=0.5
    else:
        raise ValueError('error')
    if np.random.random()<fim_false_thres:
        """ar的文件数量"""
        FileterCounter.file_fim_false+=1
        FileterCounter.file_fim_false_token_num+=len(new_content_iter)
        return True,{'new_content':new_content_iter}
    # filepath_iter=filepaths_list_iter[0]
    filepath=node.filepath
    language=node.language
    # assert node.language is not ''
    assert node.language != ''
    parser=PaserCodeFile.lang_parse_proxy.get_parser(lang=language)
    if not parser:
        # fim_string_list_per_node=[]
        mock_parser_codefile_obj=MockParserCodeFile()
        extract_no_parse_node_info_obj_list=mock_parser_codefile_obj.use_fim_process_file(content=new_content_iter,debug_node=node)
        psm_text_tuple_list=[node_iter.get_fim_text_tuple() for node_iter in extract_no_parse_node_info_obj_list]
        fim_string_list_per_node,fim_string_per_node_concat=FIMProxy.batch_concat_fim_of_deepseek(
                psm_text_tuple_list=psm_text_tuple_list,
                bool_with_normal=True)
        FileterCounter.mock_parser+=1
        FileterCounter.mock_parser_token_num+=len(fim_string_per_node_concat)
        return_dict={
            'fim_string_list_per_node':fim_string_list_per_node,
            'new_content':fim_string_per_node_concat,
            'deal_method':'no_parser_fim'
        }
        return True,return_dict
    #从文件解析 fim parser node
    kept_node_list_iter=PaserCodeFile.use_fim_process_file(filepath)
    if not kept_node_list_iter:
        FileterCounter.file_fim_false+=1
        FileterCounter.file_fim_false_token_num+=len(new_content_iter)
        return True,{'new_content':new_content_iter}
    if len(kept_node_list_iter)>1:
        try:
            # assert kept_node_list_iter[-1].context_start_index>=kept_node_list_iter[0].context_start_index
            assert kept_node_list_iter[-1].middle_arange[0]>=kept_node_list_iter[0].middle_arange[0]
        except AssertionError as e:
            context_start_index_list=[(check_node_iter.context_start_index,check_node_iter.context_end_index) for check_node_iter in kept_node_list_iter]
            print('context_start/end_index_list=\n',context_start_index_list)
            raise ValueError('AssertionError')
    fim_string_list_per_node=[]
    fim_string_per_node_concat=''
    for kept_node_iter in kept_node_list_iter:
        prefix_part=kept_node_iter.prefix_part
        suffix_part=kept_node_iter.suffix_part
        middle_part=kept_node_iter.middle_part
        ds_format_string=FIMProxy.concat_fim_of_deepseek(prefix=prefix_part,suffix=suffix_part,
                                                         middle=middle_part)
        fim_string_list_per_node.append(ds_format_string)
        fim_string_per_node_concat+=ds_format_string
        #单个fim 级别的统计数量
        FileterCounter.fim_sample_counter+=1
    FileterCounter.file_fim_sample_counter+=1
    FileterCounter.file_fim_sample_counter_token_num+=len(fim_string_per_node_concat)
    if not fim_string_list_per_node:
        #解析文件,希望fim,一个都解析不出来的文件数量
        FileterCounter.file_fim_false+=1
        FileterCounter.file_fim_false_token_num+=len(new_content_iter)
        return True,{'new_content':new_content_iter}
    FileterCounter.file_fim_true+=1
    FileterCounter.file_fim_true_token_num+=len(fim_string_per_node_concat)
    return_dict={
        'fim_string_list_per_node':fim_string_list_per_node,
        'new_content':fim_string_per_node_concat,
        'deal_method':'parser_fim'
        }
    return True,return_dict
# @timeit
def concat_text_by_graph(stack:List[PathNode],extra_dirpath_str)->List[Text]:
    """
        常规的遍历和连接函数，用于处理小文件
        >50M,则独立一个sample
        行粒度切分组合content,非完整的content
    """
    
    # GRAPH_FILE_MAX_SIZE=int(os.environ['GRAPH_FILE_MAX_SIZE'])
    GRAPH_CONTENT_MAX_SIZE=int(os.environ['GRAPH_CONTENT_MAX_SIZE'])
    context_list=[]
    current_context=''
    for node_iter in stack:
        # bool_content,new_content_iter=process_pathnode(node_iter=node_iter)
        # if not bool_content:
        #     continue
        bool_content,ret_content_dict=process_pathnode_with_fim(node=node_iter,source='stack',bool_fim=True)
        if not bool_content:
            ##process_pathnode_with_fim 已经统计过
            continue
        new_content_iter=ret_content_dict['new_content']
        current_context+=new_content_iter
    if not current_context:
        print('concat_text_by_graph 堆栈图中 current_context is empty')
        return context_list
    # if current_context:
    content_window_size=GRAPH_CONTENT_MAX_SIZE
    if len(current_context)>content_window_size:
        # new_content_iter_slices=split_current_context_by_window(current_context=current_context)
        new_content_iter_slices,_=split_current_content_by_line(content_window_size=content_window_size,current_context=current_context)
        try:
            assert new_content_iter_slices[-1].endswith('\n') or new_content_iter_slices[-1].endswith('>'),print(f'行数量={len(new_content_iter_slices)},new_content_iter_slices[-1]长度={len(new_content_iter_slices[-1])},new_content_iter_slices[-1][-100:]=\n{new_content_iter_slices[-1][-100:]}')
        except AssertionError as e:
            FileterCounter.window_content_end_not_normal+=1
            if np.random.random()<0.05:
                print(f'new_content_iter_slices[-1][-100:]={new_content_iter_slices[-1][-100:]},按行切分后最后的结尾符不是 \n,<end of sentence>,待排查')
        FileterCounter.split_by_content_window_size+=1
    else:
        new_content_iter_slices=[current_context]
        FileterCounter.not_split_by_content_window_size+=1
    #check
    context_list.extend(new_content_iter_slices)
    check_length_after_concat=len(''.join(context_list))
    assert check_length_after_concat==len(current_context),print(f'len(current_context)={len(current_context)},length_after_concat={check_length_after_concat}')
    return context_list
