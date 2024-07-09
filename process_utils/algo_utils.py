import numpy as np
from fuzzywuzzy import fuzz
from typing import List,Dict,Text
from process_utils.constants import Constants
from process_utils.utils import remove_personal_path_prefix

def hamming_distance(x1,x2):
    length=max(len(x1),len(x2))
    distance=sum(xi == yi for xi, yi in zip(x1[:length], x2[:length]))
    dist_ratio=distance/length
    return dist_ratio

def jaccard_distance(set1,set2):
    """
        对 计算字符串的左右位置感知的相似度
    """
    if len(list(set1))==0 or len(list(set2))==0:
        return -1,-1,-1
    cocon_words_num=len(list(set1.intersection(set2)))
    left_sim=cocon_words_num/len(list(set1))
    right_sim=cocon_words_num/len(list(set2))
    union_sim=cocon_words_num/len(list(set2))
    return left_sim,right_sim,union_sim

def calc_edit_sim_per_sample(pred,gt):
    """
        与cceval的 es计算对齐
    """
    return fuzz.ratio(pred, gt)


def cacl_distance_by_jaccard_of_pair_wise(words1,words2):
    min_length=min(len(words1),len(words2))
    similarity=len(set(words1).intersection(set(words2)))/min_length
    return similarity

class DependPathFounder(object):
    project_root_2_lang_2_filepath_2_filepath_list_dict={}

    @staticmethod
    def init_static_variable(project_root_2_lang_2_filepath_2_filepath_list_dict):
        assert len(DependPathFounder.project_root_2_lang_2_filepath_2_filepath_list_dict)==0
        DependPathFounder.project_root_2_lang_2_filepath_2_filepath_list_dict=project_root_2_lang_2_filepath_2_filepath_list_dict

    @staticmethod
    def pick_most_match_path(imports:List[Text],import_src_filepath:Text,paths:List[Text],project_root:Text,language=Constants.LANG_CPP):
        """
            找到import_src_filepath依赖的所有文件,从 filepath2filepath mapping中
            和paths取交集,用于计算相似度      
            warning:  filter_paths 后续处理不能＋shuffle
        """
        filter_paths=paths
        if project_root in DependPathFounder.project_root_2_lang_2_filepath_2_filepath_list_dict.keys():
            #目前仅对 vcos cpp生效
            if language in DependPathFounder.project_root_2_lang_2_filepath_2_filepath_list_dict[project_root].keys():
                    depend_filepath_list=DependPathFounder.project_root_2_lang_2_filepath_2_filepath_list_dict[project_root][language][import_src_filepath]
                    filter_paths=list(set(depend_filepath_list).intersection(set(paths)))
                    print(f'修改了filter_paths,paths={paths},filter_paths={filter_paths},\nimport_src_filepath={import_src_filepath},\n')
        similarity_list=[]
        import_src_filepath_no_prefix=remove_personal_path_prefix(filepath=import_src_filepath)
        assert '.' in import_src_filepath_no_prefix.split('/')[-1]
        split_src_path_list=import_src_filepath_no_prefix.split('/')[:-1]
        split_src_path_list=[elem for elem in split_src_path_list if elem]
        # print(f'split_src_path_list={split_src_path_list},imports={imports}')
        try:
            words1=split_src_path_list+imports
        except TypeError as e:
            error_msg=f'split_src_path_list={split_src_path_list},imports={imports}'
            raise ValueError(error_msg)
        words1=[elem for elem in words1 if elem]

        paths_no_prefix=[remove_personal_path_prefix(filepath=path_iter) for path_iter in filter_paths]
        split_path_list_no_prefix=[path_iter.split('/') for path_iter in paths_no_prefix]
        for index in range(len(split_path_list_no_prefix)):
            split_path_list_no_prefix[index]=[elem for elem in split_path_list_no_prefix[index] if elem]
        # filename=imports[-1]
        for path_words_iter in split_path_list_no_prefix:
            # path_words_iter=[elem for elem in path_words_iter if elem]
            similarity_iter=cacl_distance_by_jaccard_of_pair_wise(words1=words1,
                                                                words2=path_words_iter)
            similarity_list.append(similarity_iter)
        ##todo 所有分数均相同,只有一部分match，说明没有match的
        max_index=np.argmax(similarity_list)
        try:
            assert similarity_list[max_index]>0
        except AssertionError as e:
            err_msg1=f'至少一个part应该是相同的,max_index={max_index},similarity_list[max_index]={similarity_list[max_index]}\n similarity_list={similarity_list}\n'
            err_msg2=f'split_src_path_list={split_src_path_list},\n words1={words1},\n split_path_list_no_prefix={split_path_list_no_prefix}'
            # raise ValueError(err_msg1+'\n'+err_msg2)
        most_match_path=filter_paths[max_index]
        # if 'gen' in imports:
        #     print('***********file=gen similarity score************')
        #     print('words1=',words1)
        #     print(f'import_src_filepath={import_src_filepath},\nimport_src_filepath_no_prefix={import_src_filepath_no_prefix}')
        #     score_path_tuple_list=list(zip(similarity_list,split_path_list_no_prefix,paths_no_prefix))
        #     for score_path_tuple_iter in score_path_tuple_list:
        #         print(score_path_tuple_iter)
        return most_match_path 





# def jaccard_similarity(tokenized_query, tokenized_doc, containment=False):
#     set1 = set(tokenized_query)
#     set2 = set(tokenized_doc)
#     intersection = len(set1.intersection(set2))
#     union = len(set1) if containment else len(set1.union(set2))
#     return float(intersection) / union

# def calc_distance_by_jaccard_of_list_wise(words1:List[Text],words2_list:List[List[Text]]):
#     similarity_list=[]
#     for words2_iter in words2_list:
#         similarity_iter=cacl_distance_by_jaccard_of_pair_wise(words1=words1,words2=words2_iter)
#         similarity_list.append(similarity_iter)
#     max_index=np.argmax(similarity_list)
#     return max_index


# # imports:List[List[Text]],filanme_2_paths_dict,import_src_filepath
# def pick_most_match_path(imports:List[Text],import_src_filepath:Text,paths:List[Text]):
#     similarity_list=[]

#     import_src_filepath_no_prefix=remove_personal_path_prefix(filepath=import_src_filepath)
#     split_src_path_list=import_src_filepath_no_prefix.split('/')

#     paths_no_prefix=[remove_personal_path_prefix(filepath=path_iter) for path_iter in paths]
#     split_path_list_no_prefix=[path_iter.split('/') for path_iter in paths_no_prefix]
#     # filename=imports[-1]
#     for path_words_iter in split_path_list_no_prefix:
#         similarity_iter=cacl_distance_by_jaccard_of_pair_wise(words1=split_src_path_list+imports,
#                                                               words2=path_words_iter)
#         similarity_list.append(similarity_iter)
#     max_index=np.argmax(similarity_list)
#     most_match_path=paths[max_index]
#     return most_match_path
