import os
import json
import copy
import sys
pro_dirpath=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(pro_dirpath)
from process_utils.utils_model import load_model,load_sampling_params

def process(src_jsonpath,dst_dirpath,model_name,llm,sampling_params):
    rl_format_json_list=[]
    rl_format_json_1_list=[]
    prompts=[]
    with open(src_jsonpath,'r') as fr:
        for line in fr:
            sample_json_iter=json.loads(line)
            completion_id=sample_json_iter['completion_id']
            prompt=sample_json_iter['prompt']
            answer=sample_json_iter['answer']
            wrong_answer=sample_json_iter['wrong_answer']
            prompts.append(prompt)
            rl_format_json={
                'prompt':prompt,
                'prompt_id':completion_id,
                'chosen':[
                    {
                        'content':prompt,
                        'role':'user'
                    },
                    {
                        'content':answer,
                        'role':'assistant'
                    }
                ],
                'rejected':[
                    {
                        'content':prompt,
                        'role':'user'
                    },
                    {
                        'content':wrong_answer,
                        'role':'assistant'
                    }
                            ]
                                }
            rl_format_json_1=copy.deepcopy(rl_format_json)
            # rl_format_json_1['rejected'][1]['content']=response_str_of_model
            rl_format_json_list.append(rl_format_json)
            rl_format_json_1_list.append(rl_format_json_1)

    # prompts=prompts.append(prompt)
    response_list = llm.generate(prompts, sampling_params)
    response_str_of_model_list=[response.outputs[0].text for response in response_list]
    for index,response_str_of_model in enumerate(response_str_of_model_list):
        rl_format_json_1_list[index]['rejected'][1]['content']=response_str_of_model
    src_jsonname=src_jsonpath.split('/')[-1]
    dst_jsonname=src_jsonname.replace('.json','_rl.json')
    dst_jsonpath=os.path.join(dst_dirpath,dst_jsonname)
    with open(dst_jsonpath,'w') as fw:
        for line in rl_format_json_list:
            fw.write(json.dumps(line,ensure_ascii=False)+'\n')
    # dst_jsonpath_from_model=dst_jsonpath.replace('.json',f'_from_model_{model_name}.json')
    dst_jsonname=src_jsonname.replace('.json',f'_rl_from_model_{model_name}.json')
    dst_jsonpath_from_model=os.path.join(dst_dirpath,dst_jsonname)
    with open(dst_jsonpath_from_model,'w') as fw:
        for line in rl_format_json_1_list:
            fw.write(json.dumps(line,ensure_ascii=False)+'\n')
    print(f'写入文件路径={dst_jsonpath}')
    print(f'写入文件路径={dst_jsonpath_from_model}')
def main(src_jsonpath_list,dst_dirpath,model_name_or_path):
    model_type='vllm_pretrain'
    tp_size=1
    generation_max_tokens=128
    config_path=os.path.join(model_name_or_path,'config.json')
    model_name=model_name_or_path.split('/')[-1]
    with open(config_path,'r') as fr:
        config_json=json.load(fr)
        max_position_embeddings=config_json['max_position_embeddings']
        dtype=config_json['torch_dtype']

    model=load_model(model_name_or_path=model_name_or_path,tp_size=tp_size,model_type=model_type,
                     dtype=dtype,model_max_tokens=max_position_embeddings)
    sampling_params=load_sampling_params(temperature=0,top_p=1,generation_max_tokens=generation_max_tokens)
    for src_jsonpath in src_jsonpath_list:
        process(src_jsonpath=src_jsonpath,dst_dirpath=dst_dirpath,model_name=model_name,
                llm=model,sampling_params=sampling_params)

def check_inter_cmpl_ids(path1,path2):
    prompt_id_list=[]
    with open(path1,'r') as fr:
        for line in fr:
            info_dict_iter=json.loads(line)
            prompt_id=info_dict_iter['prompt_id']
            prompt_id_list.append(prompt_id)
    completion_id_list=[]
    with open(path2,'r') as fr:
        for line in fr:
            info_dict_iter=json.loads(line)
            completion_id=info_dict_iter['completion_id']
            completion_id_list.append(completion_id)
    print(f'len(prompt_id_list)={len(prompt_id_list)},len(completion_id_list)={len(completion_id_list)}')
    inter_part=set(prompt_id_list).intersection(set(completion_id_list))
    print(f'len(inter_part)={len(inter_part)},set(prompt_id_list)={len(set(prompt_id_list))},len(set(completion_id_list))={len(set(completion_id_list))}')

if __name__=='__main__':
    path1=''
    path2=''
    check_inter_cmpl_ids(path1=path1,path2=path2)