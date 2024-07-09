import os
from typing import Dict,Text,Tuple,List
from process_utils.constants import Constants
def pprint_args(args):
    print(f"** The job is running with the following arguments: ** **** ")
    message = '\n'.join([f'{k:<30}:   {v}' for k, v in vars(args).items()])
    print('====' * 30)
    print(message)
    print('====' * 30)

class FIMProxy(object):
    @staticmethod
    def concat_fim_of_deepseek(prefix:Text,suffix:Text,middle:Text=None):
        if not middle:
            ds_format_string='<｜fim▁begin｜>'+prefix+'<｜fim▁hole｜>'+suffix+'<｜fim▁end｜>'
        else:
            # ds_format_string='<｜fim▁begin｜>'+prefix+'<｜fim▁hole｜>'+suffix+'<｜fim▁end｜>'+middle+'<>'
            ds_format_string='<｜fim▁begin｜>'+prefix+'<｜fim▁hole｜>'+suffix+'<｜fim▁end｜>'+middle+'<｜end▁of▁sentence｜>'
        return ds_format_string
    
    @staticmethod
    def batch_concat_fim_of_deepseek(psm_text_tuple_list:List[Tuple],bool_with_normal=False)->List[Text]:
        fim_string_per_node_concat=''
        ds_format_string_list=[]
        for psm_tuple_iter in psm_text_tuple_list:
            if bool_with_normal and not psm_tuple_iter[-1] and not psm_tuple_iter[-2]:
                ds_format_string_iter=psm_tuple_iter[0]
            else:
                ds_format_string_iter=FIMProxy.concat_fim_of_deepseek(prefix=psm_tuple_iter[0],suffix=psm_tuple_iter[1],
                                            middle=psm_tuple_iter[2])
            ds_format_string_list.append(ds_format_string_iter)
            fim_string_per_node_concat+=ds_format_string_iter
        assert len(ds_format_string_list)==len(psm_text_tuple_list)
        return ds_format_string_list,fim_string_per_node_concat
    
    @staticmethod
    def trans_ar_2_fim_of_deepseek(cl_string):
        ds_format_string='<｜fim▁begin｜>'+cl_string+'<｜fim▁hole｜><｜fim▁end｜>'
        return ds_format_string

def codellama_format_string_2_deepseek_format(cl_string,bool_fim_pad_suffix=False)->Text:
    # fm_part='<FILL_ME>'
    fm_part=Constants.FM_FORMAT
    try:
        assert fm_part in cl_string
    except AssertionError as e:
        logger.info(f'AssertionError fm_part=\n{cl_string}', main_process_only=True)
        # print(f'AssertionError {fm_part} not in cl_string=\n{cl_string}')
        logger.info(f'AssertionError {fm_part} not in cl_string=\n{cl_string}', main_process_only=True)
    
    split_parts=cl_string.split(fm_part)
    if len(split_parts)==1:
        print(f'字符串内部没有{fm_part}')
        assert len(split_parts[0])>10
        if bool_fim_pad_suffix:
            ds_format_string=FIMProxy.trans_ar_2_fim_of_deepseek(cl_string=split_parts[0])
        else:
            return cl_string
    elif len(split_parts)>2:
        print(f'字符串内部多个{fm_part},数量={len(split_parts)}')
        return None
    elif len(split_parts)==2:
        ds_format_string=FIMProxy.concat_fim_of_deepseek(prefix=split_parts[0],suffix=split_parts[1])
    else:
        raise ValueError('error')
    assert 'fim▁begin' in ds_format_string
    assert 'end▁of▁sentence' not in ds_format_string
    return ds_format_string

    # try:
    #     prefix,suffix=cl_string.split(fm_part)
    # except ValueError as e:
    #     ##todo 要不要改为 deepseek形式的?
    #     error_string=f'ValueError deepseek fim有问题 不止一个 {e.args} fim_part={fm_part},part num={len(cl_string.split(fm_part))}'
    #     logger.info(error_string, main_process_only=True)
    #     # logger.info(f'data splits: {splits}', main_process_only=True)
    #     if bool_fim_pad_suffix:
    #         ds_format_string='<｜fim▁begin｜>'+cl_string+'<｜fim▁hole｜><｜fim▁end｜>'
    #         return ds_format_string
    #     else:
    #         return cl_string
    # ds_format_string='<｜fim▁begin｜>'+prefix+'<｜fim▁hole｜>'+suffix+'<｜fim▁end｜>'
    # # print('ds_format_string=\n',ds_format_string)
    # return ds_format_string