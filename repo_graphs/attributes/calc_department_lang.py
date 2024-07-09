import os
import re
import json
import collections
space_pattern=re.compile('[\t ]+')
filename_suffix_list=['py','cpp','c','h','hpp','go','sql',
            'js','ts','tsx','vue','jsx','json',
            'css','scss','sass','less'
            ]
lang_2_suffix_list_dict={
    'python':['py'],
    'go':['go'],
    'cpp':['cpp','c','h','hpp'],
    'javascript':['js','ts','tsx','vue','jsx','json','css','scss','sass','less'],
    'sql':['sql'],
    }

def get_projects_dirpath_list(src_dirpath_list):
    print_tuple=[]
    lan_2_keyword_2_counter={}
    for src_dirpath_iter in src_dirpath_list:
        # group_mark=get_group_repos_mark(src_dirpath_iter)
        # write_dirpath_iter=os.path.join(write_dirpath,group_mark)
        # if os.path.exists(write_dirpath_iter):
        #     shutil.rmtree(write_dirpath_iter)
        # os.makedirs(write_dirpath_iter,exist_ok=True)
        src_dst_path_tuple_list=[]
        file_num_list=[]
        project_names=os.listdir(src_dirpath_iter)
        for project_name in project_names:
            project_path=os.path.join(src_dirpath_iter,project_name)
            print('project_path=',project_path)
            src_dst_path_tuple=(project_path,project_name)
            src_dst_path_tuple_list.append(src_dst_path_tuple)
        
            file_num=0
            for root, dirs, files in os.walk(project_path):
                if '.git' in root:
                    continue
                for file in files:
                    # print(root,dirs,file)
                    filepath=os.path.join(root,file)
                    # bool_file_exist=os.path.exists(filepath_iter)
                    #print(bool_file_exist,filepath_iter)
                    file_suffix=file.split('.')[-1]
                    for lant_iter, suffix_list_iter in lang_2_suffix_list_dict.items():
                        if lant_iter not in lan_2_keyword_2_counter.keys():
                            lan_2_keyword_2_counter[lant_iter]={}
                        if file_suffix in suffix_list_iter:
                            with open(filepath,'r') as fr:
                                try:
                                    words=space_pattern.split(fr.read())
                                except Exception as e:
                                    continue
                                word_2_counter_dict=collections.Counter(words)
                                for word_iter,counter_iter in word_2_counter_dict.items():
                                    if word_iter not in lan_2_keyword_2_counter[lant_iter]:
                                        lan_2_keyword_2_counter[lant_iter][word_iter]=0
                                    lan_2_keyword_2_counter[lant_iter][word_iter]+=counter_iter
                                # print(word_2_counter_dict)
            print(f'after {project_path}')
            for check_k,check_v in lan_2_keyword_2_counter.items():
                print(check_k,len(check_v))
            # if file_num==0:
            #     print('project_path 0=',project_path)
            # file_num_list.append(file_num)
        # file_num_list_reverse=sorted(file_num_list,reverse=True)
        # print(src_dirpath_iter)
        # print(file_num_list_reverse)
        # print(file_num)
        # print_tuple.append((src_dirpath_iter,file_num_list_reverse,file_num))
        # print('----------------')
    # for print_tuple_iter in print_tuple:
    #     for print_tuple_iter_iter in print_tuple_iter:
    #         print(print_tuple_iter_iter)
    #     print('--------------------')
    # return src_dst_path_tuple_list  

    lan_2_keyword_2_counter_sort={}
    for lant,keyword_2_counter in lan_2_keyword_2_counter.items():
        keyword_2_counter_tuple_list=sorted(keyword_2_counter.items(),key=lambda x:x[1],reverse=True)
        keyword_2_counter_tuple_list=[tuple_iter for tuple_iter in keyword_2_counter_tuple_list if tuple_iter[1]>500]
        sort_keyword_2_counter_iter=dict(keyword_2_counter_tuple_list)
        lan_2_keyword_2_counter_sort[lant]=sort_keyword_2_counter_iter
    with open('lan_2_keyword_2_counter.json','w') as fw:
        json.dump(lan_2_keyword_2_counter_sort,fw,indent=4)        

def main():
    src_dirpath_list=['xxx',]
    src_dst_path_tuple_list=get_projects_dirpath_list(src_dirpath_list)

main()