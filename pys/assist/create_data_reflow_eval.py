import numpy as np
import json
import os
import shutil
import sys
import pymysql

sys.path.append('./')
sys.path.append('../')
sys.path.append('../../')
from process_utils.constants import FILES_DIRPATH
from process_utils.common_utils import FIMProxy,codellama_format_string_2_deepseek_format
from process_utils.parse_sql_data_utils import cursor,sql_for_multi_task
def trans_2_firefly_sft_format(eval_data_reflow_jsonpath):
    firefly_sample_str_list=[]
    with open(eval_data_reflow_jsonpath,'r') as fr:
        for line in fr:
            #dataset category  conversation_id
            # conversation:{human:xx,assist}
            line_dict=json.loads(line)
            prompt=line_dict['prompt']
            answer=line_dict['answer']
            completion_id=line_dict['completion_id']
            # completion_id=line_dict['department']
            ds_format_prompt=codellama_format_string_2_deepseek_format(cl_string=prompt,bool_fim_pad_suffix=False)
            if not ds_format_prompt:
                continue
            firefly_format_dict={
                'conversation':[
                    {
                        'human':ds_format_prompt,
                        'assistant':answer
                    }
                ],
                'dataset':'data_reflow',
                'conversation_id':completion_id,
                'category':'code_completion',
            }
            sample_str=json.dumps(firefly_format_dict,ensure_ascii=False)
            firefly_sample_str_list.append(sample_str)
    firefly_filename=eval_data_reflow_jsonpath.split('/')[-1].replace('.json','_of_firefly.json')
    dirpath='/'.join(eval_data_reflow_jsonpath.split('/')[:-1])
    write_jsonpath=os.path.join(dirpath,firefly_filename)
    with open(write_jsonpath,'w',encoding='utf-8') as fw:
        for sample_str in firefly_sample_str_list:            
            fw.write(sample_str+'\n')
    print(f'生成firefly 评估json文件,write_jsonpath={write_jsonpath}')
    return write_jsonpath
def create_eval_dataset_by_random_chosen(data_reflow_jsonpath,eval_data_reflow_jsonpath,bool_force_write=False):
# def create_eval_dataset_by_random_chosen(eval_data_reflow_jsonpath,bool_force_write=False):
    if os.path.exists(eval_data_reflow_jsonpath) and not bool_force_write:
        print('eval_data_reflow_jsonpath已存在，跳过')
        return
    completion_id_list=[]
    completion_id_sample_json_dict={}
    filename_2_sample_json_dict={}
    
    # res=cursor.execute(sql_for_multi_task)
    # # db.commit()
    # rows=cursor.fetchall()
    # all_completion_id_list=[]
    # for row in rows:        
    #     filename_iter=row['filename']
    #     completion_id=row['completion_id']
    #     completion_id_sample_json_dict[completion_id]=sample_json_iter
    #     if filename not in filename_2_sample_json_dict.keys():    
    #         filename_2_sample_json_dict[filename]=[]
    #     filename_2_sample_json_dict[filename].append(sample_json_iter)


    with open(data_reflow_jsonpath,'r') as fr:
        for line in fr:
            sample_json_iter=json.loads(line)        
            completion_id=sample_json_iter['completion_id']
            filename=sample_json_iter['filename']
            completion_id_list.append(completion_id)
            completion_id_sample_json_dict[completion_id]=sample_json_iter
            if filename not in filename_2_sample_json_dict.keys():    
                filename_2_sample_json_dict[filename]=[]
            filename_2_sample_json_dict[filename].append(sample_json_iter)
    # print(f'选择总量={len(completion_id_list)}')
    # len_before_dedup=len(completion_id_list)
    # len_after_dedup=len(list(set(completion_id_list)))
    # print('去重前 去重后数量=',len_before_dedup,len_after_dedup)

    # a=[i for i in range(1000)]
    weight=[max(len(samle_list_iter),20) for samle_list_iter in  list(filename_2_sample_json_dict.values())]
    weight=[elem/sum(weight) for elem in weight]
    filename_list_chosen=np.random.choice(list(filename_2_sample_json_dict.keys()),size=200,replace=False,p=weight)
    print(f'挑选的文件总量filename_list_chosen num={len(filename_list_chosen)}')
    sample_json_list_inall=[]
    for filename in filename_list_chosen:
        sample_json_list_iter=filename_2_sample_json_dict[filename]
        sample_json_list_inall.extend(sample_json_list_iter)
    print(f'根据文件扩展的样本总量sample_json_list_inall num={len(sample_json_list_inall)}')
    sample_list_chosen=np.random.choice(sample_json_list_inall,size=1500,replace=False)
    sample_list_chosen_dedup=[]
    completion_id_list_chosen=[]
    for sample_json_iter in sample_list_chosen:
        completion_id=sample_json_iter['completion_id']
        if  completion_id not in completion_id_list_chosen:
            sample_list_chosen_dedup.append(sample_json_iter)
            completion_id_list_chosen.append(completion_id)
    sample_list_chosen_dedup=sample_list_chosen_dedup[:1000]            
    completion_id_list_chosen_dedup=[sample_json_iter['completion_id'] for sample_json_iter in sample_list_chosen_dedup]
    print(f'挑选的样本总量sample_list_chosen={len(sample_list_chosen_dedup)}')
    # print(f'eval_completion_id_list num={len(eval_completion_id_list)}')
    # assert len(completion_id_list)==len(set(completion_id_list)),print(len(completion_id_list),len(set(completion_id_list)))
    eval_sample_list=[]
    used_completion_id_list=[]
    with open(data_reflow_jsonpath,'r') as fr:
        for line in fr:
            sample_json_iter=json.loads(line)        
            completion_id=sample_json_iter['completion_id']
            if completion_id in used_completion_id_list:    
                continue
            if completion_id not in completion_id_list_chosen_dedup:    
                continue
            used_completion_id_list.append(completion_id)
            # completion_id_list.append(completion_id)
            # if completion_id in eval_completion_id_list:
            eval_sample_list.append(line)
    print(f'写入评估文件数量={len(eval_sample_list)}')
    
    with open(eval_data_reflow_jsonpath,'w',encoding='utf-8') as fw:
        for eval_line in eval_sample_list:
            fw.write(eval_line)
    return eval_data_reflow_jsonpath
def tmp_write():
    eval_data_reflow_jsonpath='xxxx'
    tmp_path='./tmp.json'
    new_info_dict_list=[]
    with open(eval_data_reflow_jsonpath,'r',encoding='utf-8') as fr:
        # info_dict_list=[json.loads(line) for line in fr]
        # for info_dict_iter in info_dict_list:
        #     completion_id=info_dict_iter['completion_id']
        #     new_info_dict_list.append(info_dict_iter)
        for line in fr:
            # print(json.loads(line)['department'])
            new_info_dict_list.append(json.loads(line))
        # new_info_dict_list=fr.readlines()
    with open(tmp_path,'w',encoding='utf-8') as fw:        
        for new_info_dict_iter in new_info_dict_list:
            fw.write(json.dumps(new_info_dict_iter,ensure_ascii=False)+'\n')
            # fw.write(new_info_dict_iter)
def write_eval_cmpl_id_filepath(eval_data_reflow_jsonpath):
    with open(eval_data_reflow_jsonpath,'r',encoding='utf-8') as fr:        
        completion_id_list=[]
        for line in fr:
            completion_id=json.loads(line)['completion_id']
            completion_id_list.append(completion_id)
    dirpath=os.path.dirname(eval_data_reflow_jsonpath)
    write_cmpl_id_txtpath=os.path.join(dirpath,'data_reflow_completion_id_of_eval_0609.txt')
    with open(write_cmpl_id_txtpath,'w',encoding='utf-8') as fw:
        for completion_id_iter in completion_id_list:
            fw.write(completion_id_iter+'\n')
    print(f'write_eval_cmpl_id_filepath write_cmpl_id_txtpath={write_cmpl_id_txtpath}')
    return write_cmpl_id_txtpath

def main_process(data_reflow_jsonpath,eval_data_reflow_jsonpath,bool_force_write):
    create_eval_dataset_by_random_chosen(data_reflow_jsonpath,eval_data_reflow_jsonpath=eval_data_reflow_jsonpath,bool_force_write=bool_force_write)
    shutil.copy2(eval_data_reflow_jsonpath,FILES_DIRPATH)    

    write_cmpl_id_txtpath=write_eval_cmpl_id_filepath(eval_data_reflow_jsonpath=eval_data_reflow_jsonpath)
    shutil.copy2(write_cmpl_id_txtpath,FILES_DIRPATH)

if __name__ == "__main__":
   pass