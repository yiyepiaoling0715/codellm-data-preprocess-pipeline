import os
import copy
import json
from tree_sitter import Language,Parser,Tree,Node
from process_utils.constants import PROJECT_ROOT_DIRPATH,PathTemplate,Constants
from typing import Dict,List,Text



class LangJudge(object):
    ##parser 会有映射需求
    lang_alias_2_std_dict={
                'cpp':'C++',
                'c':'C',
                'c-sharp':'C#',
                'css':'CSS',
                'go':'Go',
                'html':'HTML',
                'java':'Java',
                'javascript':'Javascript',
                'json':'JSON',
                'julia':'Julia',
                'rust':'Rust',
                'verilog':'Verilog',
                'php':'PHP',
                'scala':'Scala',
                'python':'Python',
                'ruby':'Ruby',
                'typescript':'Typescript'
            }

    lang_2_suffix_jsonpath=os.path.join(PROJECT_ROOT_DIRPATH,'clean/bigcode_dataset/language_selection/programming-languages-to-file-extensions.json')
    #语言和suffix的mapping
    lang_suffix_list_dict={}
    with open(lang_2_suffix_jsonpath,'r') as fr:
        #原始的 suffix带 .
        raw_lang_suffix_list_dict=json.load(fr)
        pop_lang_list=['Text']
        for pop_lang_iter in pop_lang_list:
            if pop_lang_iter in raw_lang_suffix_list_dict.keys():
                raw_lang_suffix_list_dict.pop(pop_lang_iter)
    for k,v_list in raw_lang_suffix_list_dict.items():
        new_v_list=[elem[1:] for elem in v_list]
        lang_suffix_list_dict[k]=new_v_list
        for check_v in new_v_list:
            assert not check_v.startswith('.')
    print(f'{Constants.LANG_CPP}:{lang_suffix_list_dict[Constants.LANG_CPP]}\n' \
         +f'{Constants.LANG_PYTHON}:{lang_suffix_list_dict[Constants.LANG_PYTHON]},\n' \
         +f'{Constants.LANG_TS}:{lang_suffix_list_dict[Constants.LANG_TS]},\n'\
         +f'{Constants.LANG_JS}:{lang_suffix_list_dict[Constants.LANG_JS]}')
    #field  与parser无关
    lang_suffix_list_dict_no_changed=copy.deepcopy(lang_suffix_list_dict)
    #field  与parser无关
    suffix_2_lang_dict_no_changed={v_iter:k  for k,v_list in lang_suffix_list_dict_no_changed.items() for v_iter in v_list}
    #field  与parser无关
    all_allowed_language=list(lang_suffix_list_dict.keys())
    #check begin
    all_needed_suffix_list=[]
    check_suffix_2_many_lang_list=[]
    for k,v_list in lang_suffix_list_dict.items():
        for v_iter in v_list:
            if v_iter in all_needed_suffix_list:
                check_suffix_2_many_lang_list.append(v_iter)
        all_needed_suffix_list.extend(v_list)
    assert len(check_suffix_2_many_lang_list)==0, print('suffix属于多个语言',check_suffix_2_many_lang_list)
    #check end
    
    #等LangParser 赋值，other的原因
    suffix_2_lang_dict={}

    @staticmethod
    def update_lang_suffix_list_dict(part_dict:Dict):
        """
            class 初始化 时候的赋值更新
        """
        for k,v in part_dict.items():
            # assert k not in LangJudge.lang_suffix_list_dict.keys()
            LangJudge.lang_suffix_list_dict[k]=v

    @staticmethod
    def get_language_of_file(filepath):
        file_suffix=filepath.split('.')[-1]
        for lang_iter,suffix_list_iter in LangJudge.lang_suffix_list_dict.items():
            if file_suffix in suffix_list_iter:
                return lang_iter
        return None

    @staticmethod
    def get_no_change_language_of_file(file_path):
        """
            找到原始的 file suffix 对应的语言, 没有被other/cpp 等转换前的
        """
        file_suffix=file_path.split('.')[-1]
        # for lang_iter,suffix_list_iter in LangJudge.lang_suffix_list_dict.items():
        for lang_iter,suffix_list_iter in LangJudge.lang_suffix_list_dict_no_changed.items():
            if file_suffix in suffix_list_iter:
                return lang_iter
        print(f'file_path={file_path},get_no_change_language_of_file 找不到对应的语言')
        return None

    @staticmethod
    def bool_file_match_lang(language,filename):
        #只要是hi输入语言,就一定有 suffix_list, 如果suffix_list为None,说明语言名字定义不匹配
        suffix_list=LangJudge.lang_suffix_list_dict.get(language)
        # print(f"filename={filename},filename.split()[-1]={filename.split('.')[-1]},\nlanguage={language},suffix_list={suffix_list}")
        if filename.split('.')[-1] in suffix_list:
            return True
        return False

    @staticmethod
    def get_language_list_of_project(project_root):
        lang_2_counter_dict={}
        for root, dirs, files in os.walk(project_root):
            for file in files:
                suffix=file.split('.')[-1]
                assert len(LangJudge.suffix_2_lang_dict.keys())>0
                cur_lang=LangJudge.suffix_2_lang_dict.get(suffix,suffix)
                if cur_lang not in lang_2_counter_dict.keys():
                    lang_2_counter_dict[cur_lang]=0
                lang_2_counter_dict[cur_lang]+=1
        # print('project_root=\n',project_root)
        # print('lang_2_counter_dict=\n',lang_2_counter_dict)
        lang_2_counter_tuple_list=sorted(lang_2_counter_dict.items(),key=lambda x:x[1],reverse=True)
        return lang_2_counter_tuple_list

    def get_allowed_language_list_of_project(project_root):
        """
            仓库语言∩允许的语言
        """
        lang_2_counter_tuple_list=LangJudge.get_language_list_of_project(project_root=project_root)
        allowed_lang_list=[]
        for lang,count in lang_2_counter_tuple_list:
            if lang in LangJudge.all_allowed_language:
                allowed_lang_list.append(lang)
        return allowed_lang_list


    @staticmethod
    def get_top1_project_language(project_root):
        lang_2_counter_tuple_list=LangJudge.get_language_list_of_project(project_root=project_root)
        top1_lang_tuple=lang_2_counter_tuple_list[0]
        print('仓库内文件后缀&数量 top5=',lang_2_counter_tuple_list[:5])
        top1_lang=top1_lang_tuple[0]
        if top1_lang in LangJudge.lang_suffix_list_dict.keys():
            return True,lang_iter  
        # for lang_iter,suffix_list in LangJudge.lang_suffix_list_dict.items():
        #     if top1_lang in suffix_list:
        #         return True,lang_iter  
        error_info=f'ERROR,语言缺失,project_root={project_root},lang_2_counter_tuple_list={lang_2_counter_tuple_list}'
        print(error_info)
        # raise ValueError()
        return False,error_info

    @staticmethod
    def get_testcase_languages_and_suffix_list_tuple():
        testcase_languages=Constants.TESTCASE_LANG_LIST
        suffix_list_inall=[]
        for lang_iter in testcase_languages:
            suffix_list_iter=LangJudge.lang_suffix_list_dict[lang_iter]
            suffix_list_inall.extend(suffix_list_iter)
        return testcase_languages,suffix_list_inall

    @staticmethod
    def get_supported_parser_include_suffix_list():
        suffix_list=[]
        langs=[Constants.LANG_PYTHON,Constants.LANG_CPP,Constants.LANG_Go]
        for lang_iter in langs:
            suffix_list_iter=LangJudge.lang_suffix_list_dict_no_changed[lang_iter]
            suffix_list.extend(suffix_list_iter)
        return suffix_list
class LangParserProxy(object):
    def __init__(self,work_env):
        if work_env=='LOCAL':
            pass
        elif work_env in ['LPAI','LPAI_TEST']:
            pass
        else:
            raise ValueError(f'error work_env={work_env}')
        self.create_path_template(work_env=work_env)
        self.get_tree_sitter_parser_supported_language()
        self.lang_2_parser_dict=self.build_parser_dict(work_env=work_env)
    
    def create_path_template(self,work_env):
        if work_env=='LOCAL':
            self.repo_paths_dir=PathTemplate.local_tree_sitter_depend_dir
        elif work_env in ['LPAI','LPAI_TEST']:
            self.repo_paths_dir=PathTemplate.lpai_tree_sitter_depend_dir
        else:
            raise ValueError('error')
        self.output_path_template=os.path.join(self.repo_paths_dir,'build/{lang}-languages.so')
        self.repo_paths_template=os.path.join(self.repo_paths_dir,'tree-sitter-{lang}')
        print(f'work_env={work_env},repo_paths_dir={self.repo_paths_dir}')

    def get_tree_sitter_parser_supported_language(self):
        sub_dirs=os.listdir(self.repo_paths_dir)
        sub_dirs=[sub_dir for sub_dir in sub_dirs if sub_dir.startswith('tree-sitter')]
        language_list=[]
        for sub_dir in sub_dirs:
            lang_iter=sub_dir.replace('tree-sitter-','')
            language_list.append(lang_iter)
        return language_list

    def build_parser_dict(self,work_env):
        lang_2_parser_dict={}
        # langs=['cpp','c','go','java','javascript','python']
        wrong_language_list=[]
        for lang_iter in self.get_tree_sitter_parser_supported_language():    
            output_path_iter=self.output_path_template.format(lang=lang_iter)
            repo_paths_iter=self.repo_paths_template.format(lang=lang_iter)
            print(f'build_parser_dict output_path_iter={output_path_iter},\nrepo_paths_iter={repo_paths_iter}')
            if lang_iter in ['typescript','php']:
                repo_paths_iter=os.path.join(repo_paths_iter,lang_iter)
            try:
                # if lang_iter in ['cpp']:
                if False:
                    pass
                else:
                    Language.build_library(
                        output_path_iter,
                        [repo_paths_iter]
                    )
                lang_compile_iter = Language(output_path_iter, lang_iter)
                parser = Parser()
                parser.set_language(lang_compile_iter)
            except AttributeError as e:
                print(f'语言编译错误lang={lang_iter},msg={e.args}')
                wrong_language_list.append(lang_iter)
                try:
                    print(e.with_traceback())
                except Exception as e:
                    print(f'错误信息:{e}')
                continue
            except (ValueError,FileNotFoundError) as e:
                print(f'语言编译错误lang={lang_iter},msg={e.args}')                
                wrong_language_list.append(lang_iter)                
                continue
            ##
            std_lang_name=LangJudge.lang_alias_2_std_dict.get(lang_iter,lang_iter)
            lang_2_parser_dict[std_lang_name]=parser
            print(f'处理语言parser={lang_iter}')
        # for wrong_language_iter in wrong_language_list:
            # self.get_tree_sitter_parser_supported_language().remove(wrong_language_iter)
        return lang_2_parser_dict

    def get_parser(self,lang):
        """
            获取语言对应的parser, 没有则返回空,不走parser处理
        """
        if not lang in self.lang_2_parser_dict.keys():
            # print(f'parser支持的语言包括{self.lang_2_parser_dict.keys()},\n当前语言{lang}没有被支持')
            return None
        try:
            return self.lang_2_parser_dict[lang]
        except KeyError as e:
            print('lang_2_parser_dict=\n',self.lang_2_parser_dict)
            raise TypeError


