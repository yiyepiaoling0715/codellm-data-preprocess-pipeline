import json
import numpy as np
from sklearn.metrics import confusion_matrix
import copy
class DataChoice:
    def __init__(self, lang,label, data_choice):
        self.lang = lang
        self.label = label
        self.data_choice = data_choice


def frange(start, stop, step):
    while start < stop:
        yield start
        start += step

# for i in frange(0, 1, 0.1):
#     print(i)

def calc_thres(jsonpath):
    """
        计算logp的阈值
    """
    tuple_list_all_samples=[]
    with open(jsonpath, 'r') as fr:
        for line in fr:
            index_line_json=json.loads(line)
            for index,line_json in index_line_json.items():
                date_choices=line_json['date_choices']
                date_choices=json.loads(date_choices)
                language=line_json['language']
                bool_accepted=line_json['bool_accepted']
                copilot_model=line_json['copilot_model']
                if not copilot_model:
                    continue
                if 'deepseek' not in copilot_model:
                    if 'llama' not in copilot_model:
                        print(f'过滤 copilot_model={copilot_model}')
                    continue
                
                if 'ep' not in copilot_model:
                    # print(copilot_model)
                    continue
                for elem in date_choices:
                    # print(elem)
                    # print(elem.keys())
                    if isinstance(elem,dict) and 'choice_info' in elem.keys():
                        output_stat=elem['choice_info']['output_stat']
                        logprobs=output_stat['logprobs']
                        tuple_list_per_sample=[]
                        logs_per_sample=[]
                        for logprob in logprobs:
                            p_iter=logprob[list(logprob.keys())[0]]['p'] 
                            r_iter=logprob[list(logprob.keys())[0]]['r'] 
                            t_iter=logprob[list(logprob.keys())[0]]['t'] 
                            if r_iter in [1,'1']:
                                prob=np.exp(float(p_iter))
                                tuple_iter=(round(p_iter,4),round(prob,4),r_iter,t_iter)
                                logs_per_sample.append(tuple_iter)                        
                        tuple_list_per_sample=[language,bool_accepted,[],logs_per_sample]
                        tuple_list_all_samples.append(tuple_list_per_sample)
    pos_num=len([elem for elem in tuple_list_all_samples if elem[0]==1])
    neg_num=len([elem for elem in tuple_list_all_samples if elem[0]==0])
    print(f'len(tuple_list_all_samples)={len(tuple_list_all_samples)},pos_num={pos_num},neg_num={neg_num}')

    data_tuple_list=[]

    for prob_len_iter in range(9):
        tuple_list_all_samples_copy=copy.deepcopy(tuple_list_all_samples)
        bool_normal=True
        for elem in tuple_list_all_samples_copy:
            for   in frange(0,1,0.05):
                # print(len(elem[2]))
                try:
                    probs_cur=[prob_tuple_iter[1] for prob_tuple_iter in elem[3]][:prob_len_iter+1]
                    
                    men_prob_cur=sum(probs_cur)/len(probs_cur)
                    # pred_iter=1 if elem[3][:i][1]>thres_iter else 0
                    pred_iter=1 if men_prob_cur>thres_iter else 0
                    elem[2].append(pred_iter)
                    # print(f'men_prob_cur={men_prob_cur},probs_cur={probs_cur},elem[2]={elem[2]}')
                except (IndexError,ZeroDivisionError) as e:
                    # print(elem)
                    # print(e.args)
                    bool_normal=False
                    continue
            if  bool_normal:
                # assert len(elem[2])==11,print(elem[2])
                assert len(elem[2])==20,print(elem[2])
            else:
                continue
                
        groundtruth_list=[elem[1] for elem in tuple_list_all_samples_copy]
        pred_list=[elem[2] for elem in tuple_list_all_samples_copy]

        useful_index_list=[index for index,elem in enumerate(pred_list) if len(elem)>2 and elem[2]]
        useful_groundtruth_list=[groundtruth_list[useful_index] for useful_index in useful_index_list]
        useful_pred_list=[pred_list[useful_index] for useful_index in useful_index_list]
        # print(groundtruth_list)
        # print(pred_list)
        # for used_token_num in range(5):
        for index_thres,thres_iter in enumerate(frange(0,1,0.05)):
            useful_pred_list_iter=[elem[index_thres] for elem in useful_pred_list]

            calc_matrix=confusion_matrix(y_true=useful_groundtruth_list,y_pred=useful_pred_list_iter)
            #(tn, fp, fn, tp)
            ravel_vals=calc_matrix.ravel()
            new_accept_ratio=round(ravel_vals[3]/(ravel_vals[3]+ravel_vals[1]),4)
            kept_pos_ratio=round(ravel_vals[3]/(ravel_vals[2]+ravel_vals[3]),4)
            del_pos_ratio=round(ravel_vals[2]/(ravel_vals[2]+ravel_vals[3]),4)
            del_neg_ratio=round(ravel_vals[0]/(ravel_vals[0]+ravel_vals[1]),4)
            raw_accept_ratio=sum(useful_groundtruth_list)/len(useful_groundtruth_list)

            all_kept_ratio=raw_accept_ratio*kept_pos_ratio+(1-raw_accept_ratio)*(1-del_neg_ratio)

            data_tuple_iter={'ravel_vals':calc_matrix,'ravel_vals':ravel_vals,'new_accept_ratio':new_accept_ratio,
                             'kept_pos_ratio':kept_pos_ratio,'del_pos_ratio':del_pos_ratio,
                             'del_neg_ratio':del_neg_ratio,'raw_accept_ratio':raw_accept_ratio,
                             'all_kept_ratio':all_kept_ratio,'prob_len_iter':prob_len_iter+1,
                             'thres':round(thres_iter,4)
                             }
            data_tuple_list.append(data_tuple_iter)
            # if all_kept_ratio>0.8:
            #     print(f'prob_len_iter={prob_len_iter+1},thres={round(thres_iter,4)},new_accept_ratio={new_accept_ratio},raw_accept_ratio={round(raw_accept_ratio,4)},del_pos_ratio={del_pos_ratio},del_neg_ratio={del_neg_ratio},kept_pos_ratio={kept_pos_ratio},all_kept_ratio={all_kept_ratio}')
            #     print(calc_matrix,ravel_vals)
    
    data_tuple_list_desc=sorted(data_tuple_list,key=lambda elem:elem['new_accept_ratio'],reverse=True)
    data_tuple_list_filter=[elem for elem in data_tuple_list_desc if elem['all_kept_ratio']>0.8]
    print('********************')
    for data_tuple_iter in data_tuple_list_filter:
        print(data_tuple_iter)

if __name__=='__main__':
    jsonpath=''
    calc_thres(jsonpath)
