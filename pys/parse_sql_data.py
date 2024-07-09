print('进入 par_sql_data.py 文件')
import sys
sys.path.append('./')
sys.path.append('../')
import json
import pymysql
import sys
import os
import sys
import copy
import re
import random
import collections
import numpy as np
import socket
import shutil
import datetime
from typing import Dict,List
from process_utils.dedup_content import ContentPattern
from process_utils.lang_processor import LangJudge
from process_utils.path_utils import split_path_by_sep
from process_utils.parse_sql_data_utils import (
    has_repeated_subsequence,
    calc_lens,
    get_all_repo_names,
    sql_for_multi_task,
    cursor,
    sql_for_multi_task
            )
from process_utils.dedup_content import DeDupSpanForSft,DeDupSpan
from pys.assist.create_data_reflow_eval import trans_2_firefly_sft_format

if socket.gethostbyname(socket.gethostname())=='192.168.4.60':
    os.environ['LPAI_TOKEN']='123'

sys.path.append('../')
print('sys.argv[0]=',sys.argv[0])


try:
    from pys.utils import create_and_update_dataset,preheat_dataset
except ModuleNotFoundError as e:
    print('ModuleNotFoundError=',e.args)
    from utils import create_and_update_dataset,preheat_dataset

try:
    from pys.utils_fim import BaseModel
except ModuleNotFoundError as e:
    print('ModuleNotFoundError=',e.args)
    from utils_fim import BaseModel


class Counter:
    counter_in_eval=0
    counter_not_in_eval=0
    counter_no_department=0
    counter_accepted=0
    counter_not_accepted=0

    counter_dymaic_last=0

    #漏洞形数据统计
    counter_sample_inall=0
    counter_no_path_split=0
    counter_repo_out_of_pretrain=0
    counter_filename_ovelap_of_eval=0
    counter_dedup_cmpl_id=0

    filename_counter_gt_number_ge_5=0
    counter_lq_min_prefix_lq=0
    counter_lq_min_suffix_lq=0

    counter_prefix_suffix_re_error=0
    counter_search_group=0
    counter_search_empty=0
    # counter_print=0
    counter_print_in_response=0

    counter_groundtruth_null=0
    counter_groundtruth_empty=0
    counter_gt_number_ge_5=0
    counter_gt_len_le_thres=0
    counter_gt_len_gt_thres=0
    
    
    counter_1st_search=0
    counter_2nd_search=0
    counter_3rd_search=0
    counter_add_linebracket_split_line=0
    counter_double_linebracket=0


    counter_prefix_or_suffix_none=0
    # counter_lq_min_suffix=0
    counter_lq_min_prefix=0
    counter_lq_min_prefix_tokens=0
    counter_lq_min_suffix_tokens=0

    #重合数据 suffix&response
    countera_inter_of_response_and_prefix=0
    countera_inter_of_response_and_suffix=0
    


    @staticmethod
    def print_counter():
        counter_name_des={
        '单文件名':Counter.counter_no_path_split,
        '预训练repo外':Counter.counter_repo_out_of_pretrain,
        '评估集文件路径重合':Counter.counter_filename_ovelap_of_eval,
        'cmpl_id重复':Counter.counter_dedup_cmpl_id,
        'sample同意文件数量>5':Counter.filename_counter_gt_number_ge_5,
        '用于正则的prefix长度低于阈值':Counter.counter_lq_min_prefix_lq,
        '用于正则的suffix长度低于阈值':Counter.counter_lq_min_suffix_lq,
        'prefix+suffix正则error':Counter.counter_prefix_suffix_re_error,
        '正则匹配不到答案':Counter.counter_search_group,
        '正则匹配到答案但为空':Counter.counter_search_empty,
        '答案单行且包括print':Counter.counter_print_in_response,
        '有效答案为空':Counter.counter_groundtruth_null,
        '有效答案为空2':Counter.counter_groundtruth_empty,
        '答案数量超过5个被过滤掉的数量':Counter.counter_gt_number_ge_5,
        '答案长度低于阈值':Counter.counter_gt_len_le_thres,
        '答案长度高于阈值':Counter.counter_gt_len_gt_thres,
        '回流数据prefix/suffix为空':Counter.counter_prefix_or_suffix_none,
        '回流数据和上一行有重复行':Counter.countera_inter_of_response_and_prefix,
        '回流数据和下一行有重复行':Counter.countera_inter_of_response_and_suffix,
        # '样本总量':counter_sample_inall,
        # '样本总量':counter_sample_inall,
        # '样本总量':counter_sample_inall,
        # '样本总量':counter_sample_inall,
        # '样本总量':counter_sample_inall
    }
        print('样本总量',Counter.counter_sample_inall)
        Counter.counter_dymaic_last=Counter.counter_sample_inall
        
        for k,v in counter_name_des.items():
            Counter.counter_dymaic_last-=v
            print(f'{k},{v},剩余样本量={Counter.counter_dymaic_last}')        

        counter_edit_des={
            "多换行归一":Counter.counter_double_linebracket,
            "最短子串1次匹配": Counter.counter_1st_search,
            "最短子串2次匹配": Counter.counter_2nd_search,
            "最短子串3次匹配": Counter.counter_3rd_search,
            "行切分":Counter.counter_add_linebracket_split_line
        }

        for k,v in counter_edit_des.items():
            Counter.counter_dymaic_last-=v
            print(f'{k},{v}')        

        



print_completion_id=[
        # "cmpl-0f9c65f9-ddf8-45c5-b3ad-52880e8c55ba",
        # 'cmpl-501f1adb-4115-45b3-8638-9d85e57aa06d','cmpl-500a542b-7787-4b94-a353-f30bc8c4d099''cmpl-2c58611b-0430-4036-b631-3bdd96d2e474','cmpl-35280724-8ce2-4a97-9453-a518f2027ecb','cmpl-c3c13453-ddaa-415e-9e83-25186aa401bb',
        # 'cmpl-a2220c28-95a5-43df-8961-107ac45a3951',
        # 'cmpl-f210344f-311c-4389-943c-4b5dee70a34f','cmpl-be472cbb-88ed-4443-982e-346a181842f0',
        # 'cmpl-23a0521e-986f-431c-9144-3e4b35c3f44c','cmpl-3ec1cbfb-bf48-424f-a9b2-b3e4af06a4dd',
        # 'cmpl-441a7920-b3ff-4cce-af6a-f77201bbcffe','cmpl-05e0274c-961c-4e7a-8cc6-54c9431b2861'
        # 'cmpl-d2db757b-f46b-47a0-b794-9207c76b01f3','9adf1f1f-5937-419c-9999-fe4c784b291f'
        'cmpl-86fe5798-56c9-4d66-a4dc-70b701d5c8fc'
                    ]

def get_eval_jsonpath():
    root_dirpath=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # eval_jsonpath=os.path.join(root_dirpath,'files/data_reflow_of_eval_0320.json')
    # eval_jsonpath=os.path.join(root_dirpath,'files/data_reflow_of_eval_0520.json')
    eval_jsonpath=os.path.join(root_dirpath,'files/data_reflow_of_eval_0609.json')
    return eval_jsonpath

def get_eval_completion_id_list():
    completion_id_list=[]
    filename_list=[]
    completion_id_2_sample_dict={}
    eval_jsonpath=get_eval_jsonpath()
    with open(eval_jsonpath,'r') as fr:
        for line in fr:
            completion_id=json.loads(line)['completion_id']
            filename=json.loads(line)['filename']
            completion_id_list.append(completion_id)
            filename_list.append(filename)
            completion_id_2_sample_dict[completion_id]=json.loads(line)   
    return completion_id_list,filename_list,completion_id_2_sample_dict

def concat_departments_2_str(row):
    l1_department=row['l1_department']        
    l2_department=row['l2_department']
    if not l1_department or not l2_department:
        # counter_no_department+=1
        bool_no_department=1
        # department='default'
        department='智能云_软件效率'
    else:   
        department=l1_department+'_'+l2_department
        bool_no_department=0
    return department,bool_no_department


def print_diverse_ratio(task_id_2_sample_dict,group_2_samples_dict,lang_2_samples_dict,group_2_lang_2_sampels_dict,group_2_line_bracket_counter_dict,lang_2_line_bracket_counter_dict,
            sample_list_of_not_accepted,sample_list_of_accepted,
            counter_prefix_or_suffix_none,counter_no_department_1,counter_no_department_2,
            counter_groundtruth_null,
            counter_groundtruth_empty,groundtruth_min_length_thres,
            counter_gt_len_le_thres,counter_gt_len_gt_thres,
            groundtruth_max_length_thres,
            counter_print_in_response,counter_gt_number_ge_5,
            filename_counter_gt_number_ge_5,
            counter_not_accepted,counter_accepted,
            counter_accepted_after_filter,counter_not_accepted_after_filter,
            counter_repo_out_of_pretrain,counter_filename_ovelap_of_eval,
            counter_double_linebracket,
            counter_no_path_split,
            counter_dedup_cmpl_id
            ):
        ##统计
    prompt_lens=[]
    response_lens=[]
    for group_iter,samples_iter in group_2_samples_dict.items():
        print(f'group_iter={group_iter},数量len(samples_iter)=={len(samples_iter)}')
        for sample_iter in samples_iter:
            prompt_lens.append(len(sample_iter['prompt']))
            response_lens.append(len(sample_iter['answer']))
    sum_samples_inall=sum([len(samples_iter) for samples_iter in group_2_samples_dict.values()])
    print('样本总量=',sum_samples_inall)
    # print(f'task_id 维度 样本总量={len(task_id_2_sample_dict)},采纳样本总量={len(sample_list_of_accepted)},没有采纳样本总量={counter_not_accepted}')
    print(f'task_id 维度 样本总量={len(task_id_2_sample_dict)},\n采纳样本总量={counter_accepted}\n'+
            f'没有采纳样本总量={counter_not_accepted},重复样本量={counter_dedup_cmpl_id},\n预训练之外过滤掉样本量={counter_repo_out_of_pretrain}\n'+
            f'评估样本filename重合数量={counter_filename_ovelap_of_eval},\n无pathsplit样本量={counter_no_path_split}\n')
    print(f'过滤后采纳样本总量={counter_accepted_after_filter},\n过滤后没有采纳样本总量={counter_not_accepted_after_filter}\n')
    
    print('*************语言&样本数量分布*************')
    lan_samples_tuple_list=sorted([(k,v) for k,v in lang_2_samples_dict.items()],key=lambda x:len(x[1]),reverse=True)
    for index_lang in range(0,len(lan_samples_tuple_list),3):
        # print(lang_iter,f'数量len(samples_iter)=={len(samples_iter)}')
        try:
            print(f'lang={lan_samples_tuple_list[index_lang][0]},sample数量={len(lan_samples_tuple_list[index_lang][1])}',
                f'lang={lan_samples_tuple_list[index_lang+1][0]},sample数量={len(lan_samples_tuple_list[index_lang+1][1])}',
                f'lang={lan_samples_tuple_list[index_lang+2][0]},sample数量={len(lan_samples_tuple_list[index_lang+2][1])}')
        except IndexError as e:
            continue
    smaples_sum_from_lang=sum([len(elem[1]) for elem in lan_samples_tuple_list])
    print('**************语言&样本数量分布占比**********************')
    for tuple_iter in lan_samples_tuple_list:
        print(f'lang={tuple_iter[0]},sample数量={len(tuple_iter[1])},占比={round(len(tuple_iter[1])/smaples_sum_from_lang,3)}')
        # print(f'lang={tuple_iter[0]},sample数量={len(tuple_iter[1])},占比={len(tuple_iter[1])/smaples_sum_from_lang*100%}')
    print('**************group&语言&样本数量分布占比**********************')
    for group_iter,lang_2_samples_dict_iter in group_2_lang_2_sampels_dict.items():
        group_smaples_sum_iter=sum([len(samples_iter) for samples_iter in list(group_2_lang_2_sampels_dict[group_iter].values())])
        lang_2_samples_dict_iter_sorted=sorted(lang_2_samples_dict_iter.items(),key=lambda x:len(x[1]),reverse=True)
        for lang_iter,samples_iter in dict(lang_2_samples_dict_iter_sorted).items():   
            print(group_iter,lang_iter,len(samples_iter),round(len(samples_iter)/group_smaples_sum_iter,3))
    print('*****************样本总量*******************')
    sum_samples_inall=sum([len(samples_iter) for samples_iter in lang_2_samples_dict.values()])
    print('样本总量=',sum_samples_inall)
    print('*****************处理方法&处理数量*******************')
    deal_method_list=[elem['deal_method'] for elem in [*sample_list_of_not_accepted,*sample_list_of_accepted]]
    deal_method_counter=collections.Counter(deal_method_list)
    print('deal_method_counter=\n',deal_method_counter)
    Counter.counter_2nd_search=deal_method_counter['2nd_search']    
    Counter.counter_3rd_search=deal_method_counter['3rd_search']
    Counter.counter_1st_search=deal_method_counter['prefix_suffix_re_search_by_length_threshold']

    
    counter_no_department=counter_no_department_1+counter_no_department_2
    print(f'没有部门的sample数量={counter_no_department},counter_prefix_or_suffix_none={counter_prefix_or_suffix_none}')
    print(f'答案为纯换行/tab/空格,去除的数量={counter_groundtruth_null},groundtruth为空数量={counter_groundtruth_empty},\
        gt长度低于阈值={groundtruth_max_length_thres}的数量={counter_gt_len_le_thres},\
        gt长度高于阈值={groundtruth_min_length_thres}的数量={counter_gt_len_gt_thres},\
        单行print数量={counter_print_in_response},答案数量超过5个被过滤掉的数量={counter_gt_number_ge_5},\
        文件多于5个被过滤掉的数量={filename_counter_gt_number_ge_5},清洗多个换行的数量={counter_double_linebracket}')

    print('*****************部门&单多行数据分布*******************')
    for k,v in group_2_line_bracket_counter_dict.items():
        print(k,v)
    print('*****************语言&单多行数据分布*******************')
    lang_2_line_bracket_counter_dict_reverse=dict(sorted(lang_2_line_bracket_counter_dict.items(),key=lambda x:x[1]['single_line'],reverse=True))
    for k,v in lang_2_line_bracket_counter_dict_reverse.items():
        if v['multi_line']>0:
            print(k,v,round(v['single_line']/v['multi_line'],3))
    
    calc_lens(prompt_lens,name='prompt')
    calc_lens(response_lens,name='answer')


# def process_data_for_evalute_by_not_accepted(rows,write_dir_path,bool_print,bool_parse_accpted_in_not_accpted=False)->List[Dict]:
def process_data_for_evalute_by_not_accepted(rows,bool_print,bool_parse_accpted_in_not_accpted=False)->List[Dict]:
    """
       interval_prefix or interval_suffix pattern删无效后为空的数据,暂不处理
       #interval_prefix (.*?)interval_suffix  search(prompt_prefix+prompt_suffix) 的数据
          vue,ts 排除，需要精准匹配， prefix/suffix 字符数分别大于阈值
       interval_prefix-【min-20char, 3\n)】 (.*?)interval_suffix--【min-20char, 3\n)】  search(prompt_prefix+prompt_suffix)
    """

    sample_list=[]
    check_sample_list=[]

    for index_row,row in enumerate(rows): 
        bool_accepted=row['bool_accepted'] 
        #是否在 未采纳中解析采纳数据
        if not bool_parse_accpted_in_not_accpted and bool_accepted:
            continue
        if bool_accepted:
            Counter.counter_accepted+=1
        else:
            Counter.counter_not_accepted+=1

        id_=row['id']        
        completion_id=row['completion_id']        
        lang=row['language'] 
        filename=row['filename'] 
       
        created_at=row['created_at']        

        #0402 add
        prompt_tokens=str(row['prompt_tokens']) 
        completion_tokens=str(row['completion_tokens']) 
        copilot_model=row['copilot_model'] 
        user_email=row['user_email'] 
        date_utc=row['date_utc'] 

        if lang in ['vue','typescript','typescriptreact','javascript','html']:
            min_prefix_len=100
            min_suffix_len=100
            min_prefix_tokens=10
            min_suffix_tokens=10
        else:
            min_prefix_len=20
            min_suffix_len=20
            min_prefix_tokens=3
            min_suffix_tokens=3
        lang=LangJudge.lang_alias_2_std_dict.get(lang,lang)
        lang_2=row['lang'] 
        department_str,bool_no_department=concat_departments_2_str(row)
        Counter.counter_no_department+=bool_no_department
        raw_prompt_str=row['prompt']        
        prompt_json=json.loads(raw_prompt_str)
        # print('prompt_json.keys()=',prompt_json.keys())
        #获取prompt中的prefix和suffix字符串作为基准
        prompt_prefix:str=prompt_json['segments']['prefix']
        prompt_suffix:str=prompt_json['segments']['suffix']
        # print('prompt_prefix=\n',prompt_prefix)
        prompt_stop=json.dumps(prompt_json['stop'],ensure_ascii=False)
        
        raw_result_str=row['result'] 
        result_json_list=json.loads(raw_result_str)
        result_json=result_json_list[0]
        result_text=result_json['text']
        # print('未采纳的result_text=',result_text)

        # if completion_id in ['cmpl-61ddf1ad-53cf-4c06-85fb-019024054aa2']:
        #     print('completion_id=',completion_id)

        ##3min后的prefix/suffix
        interval_prefix=row['prefix']
        interval_suffix=row['suffix']
        ##目前 prefix/suffix  任一为空,则不纳入数据清洗，后续优化
        ##todo  add
        if not interval_prefix or not interval_suffix:
            Counter.counter_prefix_or_suffix_none+=1
            # if completion_id in ['cmpl-61ddf1ad-53cf-4c06-85fb-019024054aa2']:
                # print('counter_prefix_or_suffix_none completion_id=',completion_id)
            continue
        #保留有效字符串
        useful_interval_prefix=''.join(ContentPattern.pattern_useful_char.findall(interval_prefix))
        useful_interval_suffix=''.join(ContentPattern.pattern_useful_char.findall(interval_suffix))
        ##prefix 有效字符串太少,不处理 deal_prefix_1
        if len(useful_interval_prefix)<min_prefix_len:
            Counter.counter_lq_min_prefix_lq+=1
            continue
        #用于  后续 正则提取时候，suffix是否+$
        bool_suffix_end=False
        if  len(useful_interval_suffix)<min_suffix_len:
            # Counter.counter_lq_min_suffix_lq+=1
            if bool_print and completion_id in print_completion_id:
                print(f"{completion_id},useful_interval_suffix counter_lq_min_suffix_lq 0",Counter.counter_lq_min_suffix_lq)
            bool_suffix_end=True
        ##如果prompt_prefix.endswith(\n),则split后有个''
        prompt_prefix_lines=prompt_prefix.split('\n')
        prompt_prefix_lines_by_keep_usefule_lines=[elem for elem in prompt_prefix_lines if ContentPattern.pattern_useful_char.search(elem)]
        #prefix 只有\n or 按照行切分再保留后的有效字符太少,   与deal_prefix_1 类似
        if not prompt_prefix_lines_by_keep_usefule_lines or len(''.join(prompt_prefix_lines_by_keep_usefule_lines))<min_prefix_len:
            Counter.counter_lq_min_prefix_lq+=1
            continue
        #suffix 只有\n or 按照行切分再保留后的有效字符太少,  
        raw_prompt_suffix_lines=prompt_suffix.split('\n')
        prompt_suffix_lines=[elem for elem in raw_prompt_suffix_lines if ContentPattern.pattern_useful_char.search(elem)]
        if not prompt_suffix_lines or len(''.join(prompt_suffix_lines))<min_suffix_len:
            Counter.counter_lq_min_suffix_lq+=1
            if bool_print and completion_id in print_completion_id:
                print(f"{completion_id},prompt_suffix_lines counter_lq_min_suffix_lq 0",Counter.counter_lq_min_suffix_lq)
            continue

        ##组成一个提取 response的正则,需要 简单&有一定量信息的prefix/suffix
        ##length>min_prefix_len, num—token>prompt_prefix_truncate_tokens_num
        prompt_prefix_truncate=prompt_prefix_lines_by_keep_usefule_lines.pop(-1)
        prompt_prefix_truncate_tokens_num=0
        while (len(prompt_prefix_truncate)<min_prefix_len or prompt_prefix_truncate_tokens_num<min_prefix_tokens) \
                and prompt_prefix_lines_by_keep_usefule_lines:
                # and prompt_prefix_lines:
            prompt_prefix_truncate=prompt_prefix_lines_by_keep_usefule_lines.pop(-1)+'\n'+prompt_prefix_truncate
            prompt_prefix_truncate_tokens_num=len(ContentPattern.pattern_chinese_eng_num_char.findall(prompt_prefix_truncate))
        if len(prompt_prefix_truncate)<min_prefix_len or prompt_prefix_truncate_tokens_num<min_prefix_tokens:
            Counter.counter_lq_min_prefix_lq+=1
            if bool_print and completion_id in print_completion_id:
                print(f"{completion_id},counter_lq_min_prefix_lq",Counter.counter_lq_min_prefix_lq)
            continue
        #上一段判断过滤后，此处认为都可用，直接用，保留原始数据
        prompt_prefix_truncate_for_extract=prompt_prefix_lines.pop(-1)
        while (len(prompt_prefix_truncate_for_extract)<min_prefix_len or prompt_prefix_truncate_tokens_num<min_prefix_tokens) \
                and prompt_prefix_lines:
            prompt_prefix_truncate_for_extract=prompt_prefix_lines.pop(-1)+'\n'+prompt_prefix_truncate_for_extract
        prompt_prefix_truncate=prompt_prefix_truncate_for_extract
        
        prompt_suffix_truncate_tokens_num=0
        # min_suffix_len=30 if lang in ('typescript','vue') else 20
        prompt_suffix_truncate=prompt_suffix_lines.pop(0)
        while (len(prompt_suffix_truncate)<min_suffix_len or prompt_suffix_truncate_tokens_num<min_suffix_tokens) and prompt_suffix_lines:
            prompt_suffix_truncate=prompt_suffix_truncate+'\n'+prompt_suffix_lines.pop(0)
            prompt_suffix_truncate_tokens_num=len(ContentPattern.pattern_chinese_eng_num_char.findall(prompt_suffix_truncate))
        ##prompt-suffix 提取不到足够的信息，不足以正则，容易误召回，则跳过
        if len(prompt_suffix_truncate)<min_suffix_len or prompt_suffix_truncate_tokens_num<min_suffix_tokens:
            Counter.counter_lq_min_suffix_lq+=1
            if bool_print and completion_id in print_completion_id:
                print(f"{completion_id},counter_lq_min_suffix_lq",Counter.counter_lq_min_suffix_lq)
            continue

        assert  len(interval_prefix)>=min_prefix_len
        # assert  len(interval_suffix)>=min_suffix_len           

        try:
            prompt_prefix_lines_str_for_re=prompt_prefix_truncate
            prompt_suffix_lines_str_for_re=prompt_suffix_truncate
            prompt_prefix_lines_str_for_re=re.escape(prompt_prefix_lines_str_for_re)
            prompt_suffix_lines_str_for_re=re.escape(prompt_suffix_lines_str_for_re)
            re_str=prompt_prefix_lines_str_for_re+'((.|\n)*?)'+prompt_suffix_lines_str_for_re
            if bool_suffix_end:
                re_str+='$'
            prefix_suffix_pattern=re.compile(re_str,re.M)
        except re.error as e:
            ##暂时不处理，eg.   # suffix = ") {\n    return 'Hello world'\n}\n"
            print(f'RE ERROR={e.args},completion_id={completion_id},re_str={re_str}')
            Counter.counter_prefix_suffix_re_error+=1
            continue
        
        interval_prefix_suffix=interval_prefix+interval_suffix
        searcher=prefix_suffix_pattern.search(interval_prefix_suffix)

        if bool_print and completion_id in print_completion_id:
            print(f'completion_id={completion_id}')
            # print(f'interval_prefix={interval_prefix}')
            print(r'interval_prefix_suffix=\n',interval_prefix_suffix)
            print(f'prompt_prefix[:-100]={prompt_prefix[-100:]}')
            print(f'interval_prefix[-100:]={interval_prefix[-100:]}')
            print(f'prompt_suffix={prompt_suffix}')
            print(f'interval_suffix={interval_suffix}')
            print('prompt_prefix_lines_str_for_re=\n',prompt_prefix_lines_str_for_re)
            print('prompt_suffix_lines_str_for_re=\n',prompt_suffix_lines_str_for_re)
            print('prefix_suffix_pattern=\n',prefix_suffix_pattern)
            print('searcher=',searcher)

        if searcher:
            # print('searcher=',searcher)
            try:
                search_result=searcher.group(1)
            except IndexError as e:
                print('IndexError=',e.args)
                print('re_str=\n',re_str)
                print('interval_prefix_suffix=\n',interval_prefix_suffix)
                print('searcher.groups()',searcher.groups())
                # search_result=searcher.groups()[0]
                Counter.counter_search_group+=1
                continue
            if not search_result:
                # 匹配有值,但为空
                Counter.counter_search_empty+=1
                continue
            if len(searcher.groups())!=2:
                print(f'len(searcher.groups()={len(searcher.groups())}')
            # print('正则匹配添加部分=\n',search_result)
            right_response=search_result
            # counter_deal_prefix+=1
            deal_method='prefix_suffix_re_search_by_length_threshold'
            if bool_print and completion_id in print_completion_id:
                print('search_result=\n',search_result)

            start_pos_1st,end_pos_1st=searcher.span(1)
            second_searcher=prefix_suffix_pattern.search(interval_prefix_suffix[start_pos_1st+5:])
            if bool_print and completion_id in print_completion_id:
                print('second_searcher=\n',second_searcher)
            if second_searcher:
                search_result=second_searcher.group(1)
                right_response=search_result
                deal_method='2nd_search'

                start_pos_2nd,end_pos_2nd=second_searcher.span(1)
                third_searcher=prefix_suffix_pattern.search(interval_prefix_suffix[start_pos_1st+start_pos_2nd+5:])
                if third_searcher:
                    # print(f'start_pos_1st={start_pos_1st},start_pos_2nd={start_pos_2nd}')
                    search_result=third_searcher.group(1)
                    right_response=search_result
                    deal_method='3rd_search'
                    # print('second_searcher=\n',second_searcher.group(1).split('\n')[0])
                    # print('third_searcher= \n',third_searcher.group(1).split('\n')[0])
                    if bool_print and completion_id in print_completion_id:
                        print(f'third_searcher right_response={right_response}')
                else:
                    # print('只有2nd searcher ,没有 3rd searcher')
                    pass

            if len(right_response)>1000 or completion_id in print_completion_id:
                ##check-begin
                interval_prefix_suffix=interval_prefix+'\n【【MIDDLE】】\n'+interval_suffix
                prompt_prefix_suffix=prompt_prefix+'\n【【MIDDLE】】\n'+prompt_suffix
                check_json_iter={
                    'prompt_prefix_suffix':prompt_prefix_suffix,
                    'interval_prefix_suffix':interval_prefix_suffix,
                    'right_response':right_response,
                    'wrong_response':result_text,
                    'id':id_,
                    'completion_id':completion_id,
                    'diff_line_index':[-1,-1],
                    'deal_method':deal_method,
                    'lang':lang,
                    'len_right_response':len(right_response)
                }
                check_sample_list.append(check_json_iter)
                ##check-end
        else:
            Counter.counter_search_empty+=1
            continue     

        if '\n\n' in right_response:
            # print('clean re 替换前',sample_iter['groundtruth'])
            right_response=DeDupSpanForSft.clean_text_by_re(right_response)
            # print(f'cmpl_id={completion_id} clean_text_by_re 清洗后的数据=right_response=\n[{right_response}]')
            # print('clean re 替换后',sample_iter['groundtruth'])
            Counter.counter_double_linebracket+=1
            assert '\n' in right_response,print(f'{completion_id}多个\\n替换后没了\\n',right_response)
        assert '\n\n' not in right_response,print(f'{completion_id}多个\\n',right_response)

        right_response_with_linebracket=DeDupSpan.split_line_by_space_and_add_linebracket(line=right_response,lang=lang)
        assert len(right_response_with_linebracket)>=len(right_response)
        if len(right_response_with_linebracket)>len(right_response):
            Counter.counter_add_linebracket_split_line+=1
        # sample_iter['groundtruth']=groundtruth_with_linebracket
        right_response=right_response_with_linebracket

        prompt = BaseModel.gen_prompt(lang, prompt_prefix, prompt_suffix)
        samplte_iter={
            'prompt': prompt,
            'prompt_prefix':prompt_prefix,
            'prompt_suffix':prompt_suffix,
            # 'right_answer': right_response,
            'answer': right_response,
            'filename':filename,
            'wrong_answer': result_text,
            'content':prompt+right_response,
            'department': department_str,
            # 'bool_accepted':0,
            'bool_accepted':bool_accepted,
            'language':lang,
            'deal_method':deal_method,
            'completion_id':completion_id,
            'id':id_,
            'prompt_stop':prompt_stop,
            'created_at':created_at,

            'prompt_tokens':prompt_tokens,
            'completion_tokens':completion_tokens,
            'copilot_model':copilot_model,
            'lang_2':lang_2,
            'user_email':user_email,
            # 'date_utc':date_utc
        }
        sample_list.append(samplte_iter)
    return {
            'sample_list':sample_list,
            'counter_no_department':Counter.counter_no_department,
            'counter_prefix_or_suffix_none':Counter.counter_prefix_or_suffix_none,
            "counter_not_accepted":Counter.counter_not_accepted,
            'counter_accepted':Counter.counter_accepted,
            'counter_double_linebracket':Counter.counter_double_linebracket,
            'check_sample_list':check_sample_list
            }


def query_of_eval_data(other_dirpath):
    ## eval_data_path 在 files/xxx
    eval_data_reflow_jsonpath=get_eval_jsonpath()
    eval_completion_id_list,eval_filename_list,eval_completion_id_2_sample_dict=get_eval_completion_id_list()

    res=cursor.execute(sql_for_multi_task)
    # db.commit()
    rows=cursor.fetchall()
    all_completion_id_list=[]
    for row in rows:        
        filename_iter=row['filename']
        completion_id=row['completion_id']
        all_completion_id_list.append(completion_id)
        if completion_id in eval_completion_id_2_sample_dict.keys():
            sample_dict_iter=eval_completion_id_2_sample_dict[completion_id]
            sample_dict_iter['filename']=filename_iter
    for eval_completion_id_iter in eval_completion_id_list:        
        assert eval_completion_id_iter in all_completion_id_list,print(f'{completion_id} 不存在于completion_id_list中',filename_iter)

    # for row_iter in rows:
    #     completion_id=row_iter['completion_id']
    #     if completion_id not in eval_completion_id_list:
    #         continue
    # not_accepted_return_dict=process_data_for_evalute_by_not_accepted(row_iter,write_dir_path,sft_dirpath,other_dirpath,bool_print,bool_parse_accpted_in_not_accpted)
    not_accepted_return_dict=process_data_for_evalute_by_not_accepted(rows,bool_print=True,bool_parse_accpted_in_not_accpted=True)
    sample_list=not_accepted_return_dict['sample_list']
    sample_list=[sample_iter for sample_iter in sample_list if sample_iter['completion_id'] in eval_completion_id_list]
    
    for sample_iter in sample_list:
        completion_id=sample_iter['completion_id']
        if completion_id in eval_completion_id_2_sample_dict.keys():
            eval_completion_id_2_sample_dict[completion_id]['answer']=sample_iter['answer']
            eval_completion_id_2_sample_dict[completion_id]['groundtruth']=sample_iter['answer']
            eval_completion_id_2_sample_dict[completion_id]['groundtruth_length']=len(sample_iter['answer'])
        else:
            # print(f'completion_id={completion_id} 在评估集,清洗处理逻辑后过滤掉')
            pass
    with open(eval_data_reflow_jsonpath,'w',encoding='utf-8') as fw:
        for _,sample_dict_iter in eval_completion_id_2_sample_dict.items():
            fw.write(json.dumps(sample_dict_iter,ensure_ascii=False)+'\n')
    firefly_write_jsonpath=trans_2_firefly_sft_format(eval_data_reflow_jsonpath)
    shutil.copy2(eval_data_reflow_jsonpath,other_dirpath)   
    shutil.copy2(firefly_write_jsonpath,other_dirpath)    

def query_prod_for_multi_task(write_dir_path,sft_dirpath,other_dirpath,bool_print=False,bool_parse_accpted_in_not_accpted=False):
    """
        args:   write_dir_path:  是sft_dirpath和other_dirpath的 parent_dirpath
                sft_dirpath 和  other_dirpath 是  write_dir_path 的 子目录
    """
    # #有user_email
    all_repo_name_set=get_all_repo_names()
    eval_completion_id_list,eval_filename_list,_=get_eval_completion_id_list()
    # for index_eval,eval_filename_iter in enumerate(list(set(eval_filename_list))):        
    #     print(f'index_eval={index_eval},评测文件路径={eval_filename_iter}')
    print(f'去重前eval文件数量={len(eval_filename_list)},去重后eval文件数量={list(set(eval_filename_list))}')
    res=cursor.execute(sql_for_multi_task)
    # db.commit()
    rows=cursor.fetchall()

    date_choices_jsonpath=os.path.join(other_dirpath,'date_choices.json')
    data_choices_info_list=[]
    for row_iter in rows:
        # print(row_iter)
        language=row_iter['language']
        filename=row_iter['filename']
        bool_accepted=row_iter['bool_accepted']
        date_choices=row_iter.get('date_choices','')
        copilot_model=row_iter.get('copilot_model','')
        if date_choices:
            data_choices_info_list.append({'language':language,'bool_accepted':bool_accepted,
                                    'copilot_model':copilot_model,'date_choices':date_choices})
    if data_choices_info_list:
        with open(date_choices_jsonpath,'w') as f:
            json.dump(dict(enumerate(data_choices_info_list)),f)

    # print('*****print sql data***********')

    groundtruth_min_length_thres=4
    groundtruth_max_length_thres=500

    groundtruth_list=[]

    if not bool_parse_accpted_in_not_accpted:
        sample_list_of_accepted,counter_no_department_1=process_data_for_evaluate_by_accepted(rows=rows)
    else:
        sample_list_of_accepted=[]
        counter_no_department_1=0
    assert not sample_list_of_accepted
    used_completion_id_list=set()
    dedup_rows_by_completion_id=[]
    Counter.counter_sample_inall=len(rows)
    print(f'begin dedup')
    filepath_set=set()
    department_2_user_email_2_pretrain_repo_counter_dict={}
    for row_iter in rows:        
        completion_id=row_iter['completion_id']
        filename=row_iter['filename']
        #去掉重复的 completion_id
        if completion_id in used_completion_id_list:   
            Counter.counter_dedup_cmpl_id+=1         
            continue
        
        filename=row_iter['filename'] 
        user_email=row_iter['user_email'] 
        department=concat_departments_2_str(row_iter)
        if department not in department_2_user_email_2_pretrain_repo_counter_dict.keys():
            department_2_user_email_2_pretrain_repo_counter_dict[department]={}
        if user_email not in department_2_user_email_2_pretrain_repo_counter_dict[department].keys():
            department_2_user_email_2_pretrain_repo_counter_dict[department][user_email]={'in_repo':0,'out_repo':0}

        bool_split,filename_parts=split_path_by_sep(filename=filename)
        if not bool_split:
            Counter.counter_no_path_split+=1
            if not BOOL_GEN_EVAL:
                continue
        # if '/' in filename:
        #     filename_parts=filename.split('/')
        # elif "\\" in filename:
        #     filename_parts=re.escape(filename).split('\\')
        # else:
        #     #根据文件名字过滤,Unitile这种过滤
        #     # print(f'无文件路径分隔符 error filename={filename}')
        #     Counter.counter_no_path_split+=1
        #     if not BOOL_GEN_EVAL:
        #         continue
        if BOOL_GEN_EVAL:
            dedup_rows_by_completion_id=rows
        else:
            # #重新 生成 eval 评估集 begin
            filename_parts=[part_iter.replace('_','').replace('-','').lower() for part_iter in filename_parts]
            # #过滤掉不在pretrain仓库内的文件
            if not set(filename_parts).intersection(all_repo_name_set):
                # print('非预训练repo filename=',filename)
                Counter.counter_repo_out_of_pretrain+=1
                # if '_' in filename_parts[-1] or '-' in filename_parts[-1]:
                #     print('_-filename=',filename)
                # if filename not in filepath_set:
                #     print('非预训练repo filename=',filename)
                filepath_set.add(filename)      
                department_2_user_email_2_pretrain_repo_counter_dict[department][user_email]['out_repo']+=1
                continue
            department_2_user_email_2_pretrain_repo_counter_dict[department][user_email]['in_repo']+=1
            #根据eval的文件名字过滤
            if not BOOL_GEN_EVAL and filename in eval_filename_list:
                Counter.counter_filename_ovelap_of_eval+=1
                # print(f'过滤掉的与eval_filename_list overlapd filename={filename}')
                continue
            used_completion_id_list.add(completion_id)
            dedup_rows_by_completion_id.append(row_iter)
            # #重新 生成 eval 评估集 end
        
    print(f'end dedup')
    print(f'len(rows)={len(rows)},len(dedup_rows_by_completion_id)={len(dedup_rows_by_completion_id)}')
    # not_accepted_return_dict=process_data_for_evalute_by_not_accepted(rows=dedup_rows_by_completion_id,write_dir_path=write_dir_path,bool_print=bool_print,bool_parse_accpted_in_not_accpted=bool_parse_accpted_in_not_accpted)
    not_accepted_return_dict=process_data_for_evalute_by_not_accepted(rows=dedup_rows_by_completion_id,bool_print=bool_print,bool_parse_accpted_in_not_accpted=bool_parse_accpted_in_not_accpted)
    sample_list_of_not_accepted=not_accepted_return_dict['sample_list']
    counter_no_department_2=not_accepted_return_dict['counter_no_department']
    # counter_prefix_or_suffix_none=not_accepted_return_dict['counter_prefix_or_suffix_none']
    # counter_not_accepted=not_accepted_return_dict['counter_not_accepted']
    # counter_accepted=not_accepted_return_dict['counter_accepted']
    # counter_double_linebracket=not_accepted_return_dict['counter_double_linebracket']
    check_sample_list=not_accepted_return_dict['check_sample_list']
    # counter_repo_out_of_pretrain=not_accepted_return_dict['counter_repo_out_of_pretrain']
    counter_accepted_after_filter=0
    counter_not_accepted_after_filter=0
    groundtruth_2_counter={}
    filename_2_counter={}
    for index_sample,sample_iter in enumerate([*sample_list_of_not_accepted,*sample_list_of_accepted]):
        if sample_iter['answer'] not in groundtruth_2_counter.keys():
            groundtruth_2_counter[sample_iter['answer']]=0
        groundtruth_2_counter[sample_iter['answer']]+=1
        if sample_iter['filename'] not in filename_2_counter.keys():
            filename_2_counter[sample_iter['filename']]=0
        filename_2_counter[sample_iter['filename']]+=1
    
    task_id_2_sample_dict={}
    group_2_samples_dict={}
    lang_2_samples_dict={}
    group_2_lang_2_sampels_dict={}
    group_2_line_bracket_counter_dict={}
    lang_2_line_bracket_counter_dict={}

    print(f'数量 sample_list_of_not_accepted={len(sample_list_of_not_accepted)},sample_list_of_accepted={len(sample_list_of_accepted)}')
    sample_list_after_process=[*sample_list_of_not_accepted,*sample_list_of_accepted]
    np.random.shuffle(sample_list_after_process)
    
    sample_list_after_process=sorted(sample_list_after_process,key=lambda x:x['created_at'],reverse=False)
    for index_sample,sample_iter in enumerate(sample_list_after_process):
        department=sample_iter['department']
        language=sample_iter['language']
        completion_id=sample_iter['completion_id']
        prompt_prefix=sample_iter['prompt_prefix']
        prompt_suffix=sample_iter['prompt_suffix']

        sample_iter['metadata']={}
        sample_iter['metadata']['task_id']=f'mysql_reflow_{department}_bool_accepted_{sample_iter["bool_accepted"]}_index_{index_sample}'
        sample_iter['metadata']['repository']=f'mysql_reflow'
        sample_iter['metadata']['completion_id']=completion_id
        sample_iter['metadata']['file']=f'mysql_reflow'
        sample_iter['metadata']['context_start_lineno']=f'-1'
        sample_iter['metadata']['groundtruth_start_lineno']=f'-1'
        sample_iter['metadata']['right_context_start_lineno']=f'-1'
        sample_iter['groundtruth']=sample_iter['answer']
        sample_iter['groundtruth_length']=len(sample_iter['groundtruth'])
        
        sample_iter['prompt_tokens']=sample_iter['prompt_tokens']
        sample_iter['completion_tokens']=sample_iter['completion_tokens']
        sample_iter['copilot_model']=sample_iter['copilot_model']
        sample_iter['user_email']=sample_iter['user_email']
        # sample_iter['date_utc']=sample_iter['date_utc']
        # sample_iter['date_choices']=sample_iter['date_choices']
                
        for trans_k,trans_v in sample_iter.items():
            if trans_v is None :
                sample_iter[trans_k]=''
        if bool_print and sample_iter['completion_id'] in print_completion_id:
            check_bool_match_iter=ContentPattern.pattern_null.fullmatch(sample_iter['groundtruth'])
            print(f"check_bool_match_iter={check_bool_match_iter},groundtruth={sample_iter['groundtruth']},completion_id={sample_iter['completion_id']}")
        if not sample_iter['groundtruth']:
            Counter.counter_groundtruth_empty+=1
            continue
        if ContentPattern.pattern_null.fullmatch(sample_iter['groundtruth']):
            Counter.counter_groundtruth_null+=1
            continue
        if sample_iter['groundtruth_length']>groundtruth_max_length_thres:
            Counter.counter_gt_len_le_thres+=1
            continue
        if len(''.join(ContentPattern.pattern_useful_char.findall(sample_iter['groundtruth'])))<groundtruth_min_length_thres:
            Counter.counter_gt_len_gt_thres+=1
            continue
        if sample_iter['groundtruth_length']<groundtruth_min_length_thres:
            Counter.counter_gt_len_gt_thres+=1
            continue

        # if 'print' in sample_iter['groundtruth'] and sample_iter['groundtruth'].count('\n')<=2:
        if len(ContentPattern.print_pattern.findall(sample_iter['groundtruth']))>0 and sample_iter['groundtruth'].count('\n')<=2:
            Counter.counter_print_in_response+=1
            continue
        ##过滤重复groundtruth
        cur_groundtruth_counter=groundtruth_2_counter[sample_iter['groundtruth']]
        if cur_groundtruth_counter>3:
            if np.random.random()<(1-3/cur_groundtruth_counter):
                Counter.counter_gt_number_ge_5+=1
                continue
        if sample_iter['groundtruth_length']<10:
            if np.random.random()<0.1:
                # print('groundtruth_length<10 ',sample_iter['groundtruth'])
                pass
        cur_filename_counter=filename_2_counter[sample_iter['filename']]
        if not BOOL_GEN_EVAL and cur_filename_counter>5:
            if np.random.random()<(1-5/cur_filename_counter):
                Counter.filename_counter_gt_number_ge_5+=1
                continue
        
        #assert suffix 和 right_response 按行切分后没有重合句子
        check_suffix_list=[elem for elem in prompt_suffix.split('\n') if len(elem.strip('\r\n '))>4][:1]
        check_right_response_list=[elem for elem in sample_iter['groundtruth'].split('\n') if len(elem.strip('\r\n '))>4]
        inter_part=set(check_suffix_list).intersection(set(check_right_response_list))
        if len(check_right_response_list)<5:
            try:
                assert not inter_part,print(f'{completion_id}suffix 和 right_response 按行切分后有重合句子=\n\tcheck_suffix_list=\n{check_suffix_list},\n\tcheck_right_response_list=\n{check_right_response_list},\n\tinter_part=\n{inter_part}')
            except AssertionError as e:
                Counter.countera_inter_of_response_and_suffix+=1
                continue
        #assert suffix 和 right_response 按行切分后没有重合句子
        check_prefix_list=[elem for elem in prompt_prefix.split('\n') if len(elem.strip('\r\n '))>4][-1:]
        check_right_response_list=[elem for elem in sample_iter['groundtruth'].split('\n') if len(elem.strip('\r\n '))>4]
        inter_part=set(check_suffix_list).intersection(set(check_right_response_list))
        if len(check_right_response_list)<5:
            try:
                assert not inter_part,print(f'{completion_id}prefix 和 right_response 按行切分后有重合句子=\n\tcheck_suffix_list=\n{check_suffix_list},\n\tcheck_right_response_list=\n{check_right_response_list},\n\tinter_part=\n{inter_part}')
            except AssertionError as e:
                Counter.countera_inter_of_response_and_prefix+=1
                continue
        #check begin
        # pattern_debg_linebracket_sameline=re.compile('[\u4e00-\u9fa5a-zA-Z0-9_;,\[\]\(\)]+[\t ]{3,}[\u4e00-\u9fa5a-zA-Z0-9_;,\[\]\(\)]+')
        # linebracket_searcher=pattern_debg_linebracket_sameline.search(sample_iter['groundtruth'])
        # if linebracket_searcher:
        #     print(f'cmpl_id={completion_id} many space in sampleline, searcher={linebracket_searcher.group()},groundtruth={[sample_iter["groundtruth"]]}','可视化的=\n',sample_iter['groundtruth'])
        # if sample_iter['groundtruth'].startswith('\n'):
        #     print(f'completion_id={completion_id},groundtruth startswith \\n ',sample_iter['groundtruth'])
        #check end
        
        # if len(sample_iter['groundtruth'])!=len(groundtruth_with_linebracket):
        #     print(f"cmpl_id={completion_id},添加linebracket 切分换行,原始groundtruth=\n{sample_iter['groundtruth']},\ngroundtruth_with_linebracket=\n{groundtruth_with_linebracket}")

        #开始统计
        groundtruth_list.append(sample_iter['groundtruth'])            
        bool_multi_sub,sub,counter_repeated=has_repeated_subsequence(s=sample_iter['groundtruth'])
        # if bool_multi_sub and counter_repeated>1 and len(sub)>30 and np.random.random()<0.01:
        if bool_multi_sub and counter_repeated>1 and len(sub)>30 :
            print('局部重复的groundtruth')
            print('groundtruth=',sample_iter['groundtruth'])
            print(f'bool_multi_sub={bool_multi_sub},sub={sub},counter={counter_repeated}')

        line_bracket_num=sample_iter['groundtruth'].count('\n')
        bool_line_bracket_key='multi_line' if line_bracket_num>=1 else 'single_line'
        transed_department=department if department=='智能云_软件效率' else "非软效"
        if transed_department not in group_2_line_bracket_counter_dict.keys():
            group_2_line_bracket_counter_dict[transed_department]={'single_line':0,'multi_line':0}
        group_2_line_bracket_counter_dict[transed_department][bool_line_bracket_key]+=1
        
        transed_language='ts' if language in ['typescript','typescriptreact','vue'] else language
        if transed_language not in lang_2_line_bracket_counter_dict.keys():
            lang_2_line_bracket_counter_dict[transed_language]={'single_line':0,'multi_line':0}
        lang_2_line_bracket_counter_dict[transed_language][bool_line_bracket_key]+=1

        # if sample_iter['groundtruth_length']<10:
        #     print('short gt=',sample_iter['groundtruth_length'],sample_iter['groundtruth'])
        if department not in group_2_samples_dict.keys():
            group_2_samples_dict[department]=[]
            group_2_lang_2_sampels_dict[department]={}
        if language not in lang_2_samples_dict.keys():
            lang_2_samples_dict[language]=[]
        if language not in group_2_lang_2_sampels_dict[department].keys():
            group_2_lang_2_sampels_dict[department][language]=[]
        
        #before start 
        # group_2_samples_dict[department].append(sample_iter)
        # task_id_2_sample_dict[sample_iter['metadata']['task_id']]=sample_iter
        # lang_2_samples_dict[language].append(sample_iter)  
        # group_2_lang_2_sampels_dict[department][language].append(sample_iter)
        #before end
        #new start
        new_sample_iter=copy.deepcopy(sample_iter)
        # new_sample_iter['metadata']=json.dumps(sample_iter['metadata'],ensure_ascii=False)
        new_sample_iter['metadata']=sample_iter['metadata']
        for trans_k,trans_v in new_sample_iter.items():
            if trans_v=='' and trans_k not in ['groundtruth']:
                new_sample_iter[trans_k]='null'
            # if trans_k=='date_utc':
            #     print('trans==>',trans_k,trans_v,trans_v=='')
        assert 'department' in new_sample_iter
        group_2_samples_dict[department].append(new_sample_iter)
        task_id_2_sample_dict[sample_iter['metadata']['task_id']]=new_sample_iter
        lang_2_samples_dict[language].append(new_sample_iter)  
        group_2_lang_2_sampels_dict[department][language].append(new_sample_iter)
        #new end

        if sample_iter['completion_id'] in []:
            check_sample_list.append(sample_iter)
        if sample_iter['bool_accepted']==1:
            counter_accepted_after_filter+=1
        elif sample_iter['bool_accepted']==0:
            counter_not_accepted_after_filter+=1
        else:
            print('bool_accepted=',sample_iter['bool_accepted'],sample_iter['completion_id'])
            raise ValueError('error')

    if not os.path.exists(write_dir_path):
        os.makedirs(write_dir_path,exist_ok=True)
    if not os.path.exists(sft_dirpath):
        os.makedirs(sft_dirpath,exist_ok=True)
    
    ## for check begin
    check_sample_dict=dict(zip(range(len(check_sample_list)),check_sample_list))
    with open(os.path.join(write_dir_path,'check_sample_dict.json'),'w') as fw:
        json.dump(check_sample_dict,fw,ensure_ascii=False,indent=4)
    ## for check end

    # sft_dirpath=os.path.join(write_dir_path,'sft')
    # group_2_no_jsonpath=os.path.join(write_dir_path,'group_2_no.json')
    # departments_txtpath=os.path.join(write_dir_path,'departments.txt')
    departments_txtpath=os.path.join(write_dir_path,'departments.txt')
    write_data_path=os.path.join(sft_dirpath,'data_reflow.json')    
    
    other_write_data_path=os.path.join(other_dirpath,'data_reflow.json')
    ymd_date=datetime.datetime.now().strftime('%Y%m%d')
    write_data_path_with_ymd=other_write_data_path.replace('.json','_'+ymd_date+'.json')


    # write_data_path_1000=os.path.join(sft_dirpath,'data_reflow_1000.json')
    samples_all_from_group=[sample_iter for k,v in group_2_samples_dict.items() for sample_iter in v]
    samples_all_from_group_sort=sorted(samples_all_from_group,key=lambda x:x['created_at'],reverse=False)
    created_at_list=[sample_iter['created_at'] for sample_iter in samples_all_from_group_sort]
    print('********************top 100 accepted=********************\n',created_at_list[:10])
    print('********************tail 100 accepted=*******************\n',created_at_list[-10:])

    static_eval_jsonpath=get_eval_jsonpath()
    eval_filename=static_eval_jsonpath.split('/')[-1]
    dst_eval_jsonpath=os.path.join(other_dirpath,eval_filename)

    with open(write_data_path,'w',encoding='utf-8') as fw:
        # for k,v in group_2_samples_dict.items():
        for sample_iter in samples_all_from_group_sort:
            if sample_iter['completion_id'] in eval_completion_id_list:
                Counter.counter_in_eval+=1
                continue
            Counter.counter_not_in_eval+=1
            fw.write(json.dumps(sample_iter,ensure_ascii=False)+'\n')
    shutil.copy(write_data_path,write_data_path_with_ymd)
    shutil.copy(static_eval_jsonpath,dst_eval_jsonpath)

    print(f'counter_in_eval={Counter.counter_in_eval},counter_not_in_eval={Counter.counter_not_in_eval}')
    
    part_data_nums=[1000,3000,5000,7000]
    for part_data_num_iter in part_data_nums:
        write_data_path_iter=other_write_data_path.replace('.json',f'_{part_data_num_iter}.json')
        with open(write_data_path_iter,'w',encoding='utf-8') as fw:
            # for k,v in group_2_samples_dict.items():
            # for sample_iter in samples_all_from_group_sort[-1000:]:
            for sample_iter in samples_all_from_group_sort:
                fw.write(json.dumps(sample_iter,ensure_ascii=False)+'\n')

    # group_2_no_dict=dict(zip(group_2_samples_dict.keys(),range(len(group_2_samples_dict.keys()))))
    group_2_sample_num_dict_sorted=dict(sorted(group_2_samples_dict.items(),key=lambda x:len(x[1]),reverse=True))
    with open(departments_txtpath,'w') as fw:
        # json.dump(group_2_no_dict,fw)
        for group_iter in list(group_2_sample_num_dict_sorted.keys()):
            fw.write(group_iter+'\n')
    print('写入departments_txtpath=\n',departments_txtpath)
    print('写入write_data_path=\n',write_data_path)

    print_diverse_ratio(
            task_id_2_sample_dict=task_id_2_sample_dict,
            group_2_samples_dict=group_2_samples_dict,lang_2_samples_dict=lang_2_samples_dict,
            group_2_lang_2_sampels_dict=group_2_lang_2_sampels_dict,
            group_2_line_bracket_counter_dict=group_2_line_bracket_counter_dict,
            lang_2_line_bracket_counter_dict=lang_2_line_bracket_counter_dict,
            sample_list_of_not_accepted=sample_list_of_not_accepted,
            sample_list_of_accepted=sample_list_of_accepted,
            counter_prefix_or_suffix_none=Counter.counter_prefix_or_suffix_none,
            counter_no_department_1=counter_no_department_1,
            counter_no_department_2=counter_no_department_2,
            counter_groundtruth_null=Counter.counter_groundtruth_null,
            counter_groundtruth_empty=Counter.counter_groundtruth_empty,
            groundtruth_min_length_thres=groundtruth_min_length_thres,
            counter_gt_len_le_thres=Counter.counter_gt_len_le_thres,
            counter_gt_len_gt_thres=Counter.counter_gt_len_gt_thres,
            counter_print_in_response=Counter.counter_print_in_response,
            counter_gt_number_ge_5=Counter.counter_gt_number_ge_5,
            filename_counter_gt_number_ge_5=Counter.filename_counter_gt_number_ge_5,
            groundtruth_max_length_thres=groundtruth_max_length_thres,
            counter_not_accepted=Counter.counter_not_accepted,
            counter_accepted=Counter.counter_accepted,
            counter_accepted_after_filter=counter_accepted_after_filter,
            counter_not_accepted_after_filter=counter_not_accepted_after_filter,
            counter_repo_out_of_pretrain=Counter.counter_repo_out_of_pretrain,
            counter_filename_ovelap_of_eval=Counter.counter_filename_ovelap_of_eval,
            counter_double_linebracket=Counter.counter_double_linebracket,
            counter_no_path_split=Counter.counter_no_path_split,
            counter_dedup_cmpl_id=Counter.counter_dedup_cmpl_id
            )
    deal_method_list=[elem['deal_method'] for elem in [*sample_list_of_not_accepted,*sample_list_of_accepted]]
    deal_method_counter=collections.Counter(deal_method_list)
    print('deal_method_counter=\n',deal_method_counter)
    Counter.counter_2nd_search=deal_method_counter['2nd_search']    
    Counter.counter_3rd_search=deal_method_counter['3rd_search']
    Counter.counter_1st_search=deal_method_counter['prefix_suffix_re_search_by_length_threshold']  
    Counter.print_counter()
    print('response和suffix相同行去重数量',Counter.countera_inter_of_response_and_suffix)
    for check_department_iter,user_email_2_pretrain_repo_counter_dict_iter in department_2_user_email_2_pretrain_repo_counter_dict.items():
        for user_email_iter,pretrain_repo_counter_dict_iter in user_email_2_pretrain_repo_counter_dict_iter.items():
            print(f'department={check_department_iter},user_email_iter={user_email_iter},counter={pretrain_repo_counter_dict_iter}')    

    # groundtruth_2_counter_reverse=sorted(groundtruth_2_counter.items(),key=lambda x:x[1],reverse=True)
    # print('***********groundtruth_2_counter_reverse*************')
    # for groundtruth_iter in groundtruth_2_counter_reverse[:100]:
    #     print(groundtruth_iter[::-1])
    print(f'len(groundtruth_list)={len(groundtruth_list)},len(list(set(groundtruth_list)))={len(list(set(groundtruth_list)))}')
    if not BOOL_GEN_EVAL:
        query_of_eval_data(other_dirpath)
    print('评估集处理完毕')
if __name__=='__main__':
    BOOL_PRINT=True
    bool_parse_accpted_in_not_accpted=True
    BOOL_UPLOAD=False
    BOOL_GEN_EVAL=False

    if socket.gethostbyname(socket.gethostname())=='xxx':
        print('**************local**************')

        write_dir_path = sys.argv[1]
        sft_dirpath = sys.argv[2]
        other_dirpath = sys.argv[3]
        query_prod_for_multi_task(write_dir_path=write_dir_path,sft_dirpath=sft_dirpath,other_dirpath=other_dirpath,bool_print=BOOL_PRINT,bool_parse_accpted_in_not_accpted=bool_parse_accpted_in_not_accpted)
    else:
        print('**************remote**************')
        write_dir_path = sys.argv[1]
        sft_dirpath = sys.argv[2]
        other_dirpath = sys.argv[3]
        print('write_dir_path',write_dir_path)
        if not os.path.exists(write_dir_path):
            os.makedirs(write_dir_path,exist_ok=True)
        # query_prod(write_dir_path=write_dir_path,sft_dirpath=sft_dirpath)
        query_prod_for_multi_task(write_dir_path=write_dir_path,sft_dirpath=sft_dirpath,other_dirpath=other_dirpath,bool_parse_accpted_in_not_accpted=bool_parse_accpted_in_not_accpted)
    


