import os
import json
import sys
import jsonlines
from typing import List,Dict
sys.path.append('../')
from process_utils.openai_func import ask_llm
from process_utils.path_utils import read_xlsx_of_testcase_note
from process_utils.algo_utils import calc_edit_sim_per_sample,jaccard_distance

"""

            sample_info_dict={
                'tested_func_filepath':tested_func_filepath,
                'tested_func_description':tested_func_description,
                'test_point':test_point,
                'test_steps':test_steps,
                'depend_filepath_list':depend_filepath_list,
                'depend_func_description_list':depend_func_description_list,
                'prompt_str_with_context':prompt_str_with_context,
                'prompt_str_no_context':prompt_str_no_context,
                'prompt_str_with_context_with_note':prompt_str_with_context_with_note,
                'testcase_path':testcase_center_path,
                'testcase_func_description':testcase_func_description,
                'bool_prompt_str_with_context':bool_prompt_str_with_context,
                'bool_prompt_str_with_context_with_note':bool_prompt_str_with_context_with_note,
            }
"""

def convert_2_multi_turn_format(sample_info_dict_list:List[Dict]):
    chat_info_1_list=[]
    chat_info_2_list=[]
    chat_info_3_list=[]

    for sample_info_dict_iter in sample_info_dict_list:
        # test_point=sample_info_dict_iter['test_point']
        # test_steps=sample_info_dict_iter['test_steps']
        # tested_func_description=sample_info_dict_iter['tested_func_description']
        # depend_func_description_list:List=sample_info_dict_iter['depend_func_description_list']
        # testcase_func_description=sample_info_dict_iter['testcase_func_description']
        prompt_str_no_context=sample_info_dict_iter['prompt_str_no_context']
        prompt_str_with_context=sample_info_dict_iter['prompt_str_with_context']
        prompt_str_with_context_with_note=sample_info_dict_iter['prompt_str_with_context_with_note']
        chat_info_1={'role':'user','content':prompt_str_no_context}
        chat_info_2={'role':'user','content':prompt_str_with_context}
        chat_info_3={'role':'user','content':prompt_str_with_context_with_note}
        chat_info_1_list.append(chat_info_1)
        chat_info_2_list.append(chat_info_2)
        chat_info_3_list.append(chat_info_3)
    return chat_info_1_list,chat_info_2_list,chat_info_3_list

def write_json_list_2_jsonl(json_list:List[Dict],output_jsonl_path:str):
    with jsonlines.open(output_jsonl_path,'w') as fw:
        fw.write_all(json_list)

def convert_2_multi_turn_format_and_write_to_file(sample_info_dict_list:List[Dict],output_jsonl_path:str):
    chat_info_1_list,chat_info_2_list,chat_info_3_list=convert_2_multi_turn_format(sample_info_dict_list=sample_info_dict_list)
    #testcase_dataset_part.json
    write_jsonpath_1=output_jsonl_path.replace('.json','_sft_no_context.json')
    write_jsonpath_2=output_jsonl_path.replace('.json','_sft_with_context.json')
    write_jsonpath_3=output_jsonl_path.replace('.json','_sft_with_context_with_note.json')
    write_json_list_2_jsonl(json_list=chat_info_1_list,output_jsonl_path=write_jsonpath_1)
    write_json_list_2_jsonl(json_list=chat_info_2_list,output_jsonl_path=write_jsonpath_2)
    write_json_list_2_jsonl(json_list=chat_info_3_list,output_jsonl_path=write_jsonpath_3)

def process_gen_testcase(jsonpath):
    test_signature_2_info_dict=read_xlsx_of_testcase_note()
    sample_info_dict_list=[]
    with open(jsonpath,'r',encoding='utf-8') as fr:
        for line in fr:
            line_info_dict=json.loads(line)
            testcase_center_path=line_info_dict['testcase_center_path']
            # testcase_depend_info_dict_list=line_info_dict['testcase_depend_info_dict_list']
            testcase_depend_info_dict_list=line_info_dict['testcase_depend_info_dict_list']
            depend_func_description_list=[]
            depend_filepath_list=[]
            for testcase_depend_info_dict_iter in testcase_depend_info_dict_list:
                depend_func_text_2_info_dict_iter=testcase_depend_info_dict_iter['func_signature_2_info_dict']
                depend_filepath_iter=testcase_depend_info_dict_iter['filepath']
                assert len(depend_func_text_2_info_dict_iter)==1
                depend_func_description_iter=list(depend_func_text_2_info_dict_iter.values())[0][1]
                depend_func_description_list.append(depend_func_description_iter)
                depend_filepath_list.append(depend_filepath_iter)
            tested_func_info=line_info_dict['tested_func_info']
            func_signature_2_info_dict=tested_func_info['func_signature_2_info_dict']
            tested_func_filepath=tested_func_info['filepath']
            assert len(func_signature_2_info_dict)==1
            tested_func_description=list(func_signature_2_info_dict.values())[0][1]
            
            testcase_center_func_info_dict=line_info_dict['testcase_center_func_info_dict']
            testcase_func_signature=testcase_center_func_info_dict[0]
            testcase_func_description=testcase_center_func_info_dict[1]
            # print(f'depend_func_description_list=\n{depend_func_description_list}')
            depend_func_description_list_str='\n'.join(depend_func_description_list)
            bool_prompt_str_with_context=False
            bool_prompt_str_with_context_with_note=False
            prompt_extra_info=f"注意:1. 生成的时候不要带有 ```这种特殊字符,每次生成1个测试用例。2.生成时候不要带有任何的说明,只生成测试用例函数体即可"
            prompt_str_no_context=f"请根据给定目标函数,生成测试用例\n目标函数为\t{tested_func_description}\n"+ prompt_extra_info
                    # f"""注意:生成的时候不要带有 ```这种特殊字符,每次生成1个测试用例;按照json格式输出,key=case,value=生成的测试用例"""
            if depend_func_description_list_str:
                prompt_str_with_context=f"请根据给定函数和依赖的上下文信息,生成测试用例\n'+\
                    f'依赖的上下文信息为\t{depend_func_description_list_str}\n'+\
                    f'目标函数为\t{tested_func_description}。\n"+ prompt_extra_info
                    # f"""注意:生成的时候不要带有 ```这种特殊字符,每次生成1个测试用例;按照json格式输出,key=case,value=生成的测试用例"""
                bool_prompt_str_with_context=True
            else:
                prompt_str_with_context=prompt_str_no_context
            print(f'testcase_func_signature={testcase_func_signature}') 
            if testcase_func_signature in test_signature_2_info_dict.keys():
                test_point=test_signature_2_info_dict[testcase_func_signature]['test_point']
                test_steps=test_signature_2_info_dict[testcase_func_signature]['test_steps']
                print(f'测试点={test_point},testcase_func_signature={testcase_func_signature}')
                try:
                    prompt_str_with_context_with_note=f"请根据给定函数和依赖的上下文信息,生成测试用例\n"+\
                        f"依赖的上下文信息为\t{depend_func_description_list_str}\n"+\
                        f"测试点为\t{test_point},测试部步骤为\t{test_steps}\n" +\
                        f"目标函数为\t{tested_func_description}。\n"+ prompt_extra_info
                    bool_prompt_str_with_context_with_note=True
                except TypeError as e:
                    erro_msg=f'test_point={test_point},test_steps={test_steps}'
                    raise ValueError(erro_msg)
            else:
                prompt_str_with_context_with_note=prompt_str_with_context
                test_point=''
                test_steps=''

            sample_info_dict={
                'tested_func_filepath':tested_func_filepath,
                'tested_func_description':tested_func_description,
                'test_point':test_point,
                'test_steps':test_steps,
                'depend_filepath_list':depend_filepath_list,
                'depend_func_description_list':depend_func_description_list,
                'prompt_str_with_context':prompt_str_with_context,
                'prompt_str_no_context':prompt_str_no_context,
                'prompt_str_with_context_with_note':prompt_str_with_context_with_note,
                'testcase_path':testcase_center_path,
                'testcase_func_description':testcase_func_description,
                'bool_prompt_str_with_context':bool_prompt_str_with_context,
                'bool_prompt_str_with_context_with_note':bool_prompt_str_with_context_with_note,
            }
            sample_info_dict_list.append(sample_info_dict)
    return sample_info_dict_list


def diff_gen_testcase_by_llm_and_human_testcase(src_jsonpath,dst_jsonpath):
    mutli_es={
        'response_gen_no_context':0,
        'response_gen_with_context':0,
        'response_gen_with_context_with_note':0,
    }
    sample_info_dict_list=process_gen_testcase(jsonpath=src_jsonpath)
    convert_2_multi_turn_format_and_write_to_file(sample_info_dict_list=sample_info_dict_list,
                                                  output_jsonl_path=src_jsonpath)
    sample_info_dict_list_with_response=[]
    for index,sample_info_dict_iter in enumerate(sample_info_dict_list):
        prompt_str_no_context=sample_info_dict_iter['prompt_str_no_context']
        prompt_str_with_context=sample_info_dict_iter['prompt_str_with_context']
        prompt_str_with_context_with_note=sample_info_dict_iter['prompt_str_with_context_with_note']
        bool_prompt_str_with_context=sample_info_dict_iter['bool_prompt_str_with_context']
        bool_prompt_str_with_context_with_note=sample_info_dict_iter['bool_prompt_str_with_context_with_note']
        testcase_func_description=sample_info_dict_iter['testcase_func_description']
        response_gen_no_context=ask_llm(prompt=prompt_str_no_context)
        if bool_prompt_str_with_context:
            response_gen_with_context=ask_llm(prompt=prompt_str_with_context)
        else:
            response_gen_with_context=response_gen_no_context
        if bool_prompt_str_with_context_with_note:
            response_gen_with_context_with_note=ask_llm(prompt=prompt_str_with_context_with_note)
        else:
            response_gen_with_context_with_note=response_gen_with_context
        # print(f'response_gen_no_context={response_gen_no_context}\nresponse_gen_with_context={response_gen_with_context}\nresponse_gen_with_context_with_note={response_gen_with_context_with_note}')
        if not bool_prompt_str_with_context:
            continue
        sample_info_dict_iter['response_gen_no_context']=response_gen_no_context
        sample_info_dict_iter['response_gen_with_context']=response_gen_with_context
        sample_info_dict_iter['response_gen_with_context_with_note']=response_gen_with_context_with_note
        sample_info_dict_iter['es']={}
        sample_info_dict_iter['es']['response_gen_no_context']=calc_edit_sim_per_sample(response_gen_no_context,testcase_func_description)
        sample_info_dict_iter['es']['response_gen_with_context']=calc_edit_sim_per_sample(response_gen_with_context,testcase_func_description)
        sample_info_dict_iter['es']['response_gen_with_context_with_note']=calc_edit_sim_per_sample(response_gen_with_context_with_note,testcase_func_description)
        sample_info_dict_list_with_response.append(sample_info_dict_iter)
        if index>0 and index%10==0:

            with open(dst_jsonpath,'w') as fw:
                index_list=range(len(sample_info_dict_list_with_response))
                index_list=[str(elem) for elem in index_list]
                index_2_sample_dict=dict(zip(index_list,sample_info_dict_list_with_response))
                json.dump(index_2_sample_dict,fw,indent=4,ensure_ascii=False)
                es_dict_list=[sample_iter['es'] for sample_iter in sample_info_dict_list_with_response]                
                es_of_response_gen_no_context=[es_iter['response_gen_no_context'] for es_iter in es_dict_list]
                es_of_response_gen_with_context=[es_iter['response_gen_with_context'] for es_iter in es_dict_list]
                es_of_response_gen_with_context_with_note=[es_iter['response_gen_with_context_with_note'] for es_iter in es_dict_list]
                mutli_es['response_gen_no_context']=sum(es_of_response_gen_no_context)/len(es_of_response_gen_no_context)
                mutli_es['response_gen_with_context']=sum(es_of_response_gen_with_context)/len(es_of_response_gen_with_context)
                mutli_es['response_gen_with_context_with_note']=sum(es_of_response_gen_with_context_with_note)/len(es_of_response_gen_with_context_with_note)
            print(f'bool_prompt_str_with_context={bool_prompt_str_with_context},bool_prompt_str_with_context_with_note={bool_prompt_str_with_context_with_note}')
            print(f'testcase_func_description={testcase_func_description},\nresponse_gen_no_context={response_gen_no_context}\nresponse_gen_with_context={response_gen_with_context}\nresponse_gen_with_context_with_note={response_gen_with_context_with_note}')
            print(f'index={index},es={mutli_es}')

if   __name__ == '__main__':
    src_dirpath='xxx'
    src_jsonpath=os.path.join(src_dirpath,'testcase_dataset_part.json')
    # src_jsonpath=os.path.join(src_dirpath,'testcase_dataset.json')
    dst_filename=src_jsonpath.split('/')[-1].replace('.json','_with_llm_response.json')
    dst_jsonpath=os.path.join(src_dirpath,dst_filename)
    diff_gen_testcase_by_llm_and_human_testcase(src_jsonpath=src_jsonpath,dst_jsonpath=dst_jsonpath)