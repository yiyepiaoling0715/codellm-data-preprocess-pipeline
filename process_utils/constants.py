import os
from datasets import load_dataset,Features,Value,ClassLabel,Dataset
import pyarrow as pa

PROJECT_ROOT_DIRPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_DIRPATH=os.path.join(PROJECT_ROOT_DIRPATH,'files')
OUTPUT_DIRPATH=os.path.join(PROJECT_ROOT_DIRPATH,'output')
class Constants:
    FILEPATH_FLAG='#Path'
    #<|Assistant|>
    FILEPATH_START_TOKEN='<|PathStart|>'
    FILEPATH_END_TOKEN='<|PathEnd|>'
    # FILEPATH_START_TOKEN='Á'
    # FILEPATH_END_TOKEN='ý'

    #for fim
    TREE_SITTER_MIDDLE_IGNORE_TYPES=set([
            'string_literal',  #cpp
            'string','integer','float'   #python
            ])
    # 'unary_expression'  一元表达式
    #todo 添加对所有语言的支持
    TREE_SITTER_INTERESTING_TYPES_OF_INLINE = ['function_call','argument_list',
        'parameter_list',  #cpp parameter_list python  parameters
        'binary_expression',
        'call_expression','function_declarator','declaration_list','type_definition','translation_unit',
        'namespace_definition','conditional_expression','expression_list','assert_statement','for_in_clause',
        'list_comprehension','subscript_argument_list','base_class_clause',
        'comment',
        #python
        'parameters', 'call',
        #go
        'literal_value','literal_element','method_elem','var_declaration'
        ]
    PREFIX_WINDOW_SIZE_OF_INLINE=1000
    SUFFIX_WINDOW_SIZE_OF_INLINE=200


    TREE_SITTER_INTERESTING_TYPES_OF_MULTI_LINE = ['function_definition', 'for_statement', 'while_statement', 
        'if_statement','preproc_if','case_statement',
        'enum_specifier','switch_statement','struct_specifier','field_declaration_list','field_initializer_list','preproc_ifdef',
        'enumerator_list','macro_type_specifier','union_specifier','dictionary','try_statement','lambda_expression','lambda',
        'selector_expression','class_definition','static_assert','for_range_loop','class_specifier','function_declaration',
        'block_comment','do_statement',
        #python 多行
        'block','decorated_definition',
        #go
        'method_declaration','func_literal',
        #测试用例
        'static_assert_declaration','short_var_declaration','struct_type','method_elem','expression_switch_statement'
        ]  
    PREFIX_WINDOW_SIZE_OF_MULTI_LINE=2000
    SUFFIX_WINDOW_SIZE_OF_MULTI_LINE=400

    INTERESTING_TYPE_2_LENGTH_THRES_DICT={
        'comment':{'min':20}
    }

    #for test case
    IGNORE_TREE_SITTER_TYPES=['binary_expression','return_statement','comment','enumerator',
        'field_declaration','template_type',
        'qualified_identifier','identifier',
        'parameter_declaration','field_initializer',
        'compound_statement','expression_statement','string_content','string_literal','expression_statement'
        'parenthesized_expression','assignment_expression','declaration','init_declarator','preproc_include',
        'preproc_def','type_descriptor','preproc_call','subscript_expression','preproc_arg','array_declarator',
        'unary_expression','else_clause','field_expression','case_statement','preproc_defined','do_statement',
        'pointer_declarator','preproc_elif','number_literal','pointer_expression','cast_expression',
        'abstract_function_declarator','comma_expression','system_lib_string','labeled_statement',
        'attribute','string','initializer_pair','subscript','keyword_argument','field_designator',
        'concatenated_string','condition_clause',
          ##to remove
        'initializer_list',
        #python
        ]
    ##测试用例过滤
    #测试用例 需要保留的， class,function, attribute
    # common_exclude  for  fim and testcase
    #  测试用例  decorated_funcation,functon_definination,block 是顺序关系
    common_exclude=[
        #cpp
        'pointer_expression','expression_statement','subscript_expression',
        'subscript_argument_list','field_expression','field_designator','return_statement','array_declarator','pointer_declarator',
        'assignment_expression','2u','init_declarator' ,'declaration',';','=',',','&',')','(','!=',')','}',
        'condition_clause','update_expression','sized_type_specifier',
        'comma_expression','compound_literal_expression','pointer_type_declarator','qualified_identifier',
        'number_literal','[','initializer_pair','parenthesized_expression','cast_expression',
        'preproc_def','preproc_include','system_lib_string','preproc_defined',
        'parameter_list','parameter_declaration','parameters',  #cpp python
        'else_clause','binary_expression','return','break_statement',
        'break','static','false','while','#endif','while','unsigned','sizeof_expression',
        # 'const','primitive_type','storage_class_specifier',
        'ERROR','continue_statement',
        #python
        'def','integer','comparison_operator', 'module',
        ':','.','@','decorator',":",'string_start','string_end','assert','in','string',
        #go
        'escape_sequence','default','unary_expression','interpreted_string_literal','interpreted_string_literal',
        'package_clause','package','const'
        ]
    parent_and_sub_func_class_exclude=['argument_list','string_content',# 'function_definition',
        'string_literal','concatenated_string','initializer_list','for_statement','if_statement',
        'comment','preproc_if','while_statement','compound_statement','unary_expression',
        #适合单行
        'conditional_expression',
        # 'function_definition',
        ]
    parent_func_class_exclude=common_exclude+parent_and_sub_func_class_exclude+[
        'primitive_type','identifier',
        
        'type_descriptor','enumerator',
        'preproc_function_def','preproc_arg','preproc_else',
        
        #for test exclude
        'initializer_list',
        'type_definition','enumerator_list','enum_specifier',
        'function_declarator',
        #for test include
        #sub include
        'call_expression',

        ]
    sub_func_class_exclude=common_exclude+parent_and_sub_func_class_exclude+[
        'function_definition'
    ]

    sub_node_func_class_exclude_of_text=['struct','uint32_t']
    
    parent_func_class_include=[
                'function_declarator',]
    sub_grammer_names_include=['call_expression',
            # 'binary_expression','field_expression','assignment_expression','expression_statement',
                'conditional_expression','function_declarator',
                'primitive_type','type_descriptor',
                # for class
                'type_identifier','identifier'
                ]




    import_exclude_grammar_name_list=[
        # 'import_from_statement','import_statement','preproc_call','import_declaration',
        # 'preproc_include','import_spec_list',
        #used_import
        
        'translation_unit','preproc_elif','preproc_elif',
        #more than import 
        'preproc_else','preproc_if','preproc_ifdef',
        #part import
        # '#include','identifier','import','from','import_spec'
        #ignore
        'preproc_def','preproc_params','module',
        'comment','declaration_list','declaration','init_declarator','call_expression','qualified_identifier',
        'compound_statement','expression_statement','argument_list','template_function','string_literal','parameter_list',
        'function_definition','if_statement','function_declarator','field_declaration','field_declaration_list',
        'parameter_declaration','reference_declarator','identifier','field_expression','ssignment','call',
        'block','conditional_expression','not_operator','comment','parenthesized_expression','attribute',
        'return_statement','binary_expression','lambda_expression','template_declaration','initializer_list',
        'else_clause','struct_specifier','labeled_statement','compound_literal_expression','assignment_expression','assignment',
        'new_expression','raw_string_content','string_content','concatenated_string','namespace_definition','raw_string_literal','keyword_argument',
        'string','with_statement','with_item','with_clause','condition_clause','unary_expression','subscript_expression','alias_declaration',
        'for_statement','template_parameter_list','condition_clause','for_range_loop','template_parameter_list',
        'subscript_argument_list','update_expression','cast_expression','pointer_declarator','static_assert_declaration',
        'binary_operator','case_statement','switch_statement','ERROR','try_statement','except_clause','raise_statement',
        'class_definition','while_statement','assert_statement','parameters','dictionary','preproc_arg',
        'decorated_definition','list','yield','elif_clause','future_import_statement','string_fragment','program','block_comment',
        'line_comment','method_invocation','set','decorator','list_comprehension','augmented_assignment','generator_expression','pair',
        'catch_clause','tuple','for_in_clause','comparison_operator','boolean_operator','finally_clause',
        'subscript','comparison_operator','finally_clause','pattern_list','lambda','lambda_capture_specifier','enumerator_list',
        'preproc_function_def','throw_statement','class_specifier','enumerator_list','enum_specifier','field_initializer','class_specifier',
        'template_type','placeholder_type_specifier','optional_parameter_declaration','union_specifier','linkage_specification',
        'do_statement','template_argument_list','typed_default_parameter','abstract_function_declarator','typed_parameter',
        'field_initializer_list','type_definition','preproc_def','preproc_params','source_file','method_declaration',
        'expression_list','interpreted_string_literal','function_declaration','expression_list','interpreted_string_literal',
        'type_spec','composite_literal','selector_expression','func_literal','literal_element','go_statement',
        'short_var_declaration','assignment_statement','var_spec','struct_type','function_type','var_declaration',
        'keyed_element','var_declaration','type_declaration','type_declaration','default_case','method_elem',
        'expression_switch_statement','package_clause','const','identifier','source_file','type_qualifier',
        'dotted_name','integer','def','unary_operator','integer','print_statement'  
    ]




    FIM_LINES_NUM_THRES=15

    LANG_CPP="C++"
    #不在 LangJudge.lang_suffix_dict,已经与C++ merge
    LANG_C="C"
    LANG_PYTHON="Python"
    LANG_Go="Go"
    LANG_TS='TypeScript'
    LANG_JS='JavaScript'
    LANG_OTHER='other'

    FM_FORMAT='<FILL_ME>'

    TESTCASE_LANG_LIST=[LANG_CPP,LANG_PYTHON]

class PathTemplate:
    write_repo_json_dir='{write_dirpath}/json'
    write_repo_json_train_dir='{write_dirpath}/json/train'
    write_repo_file_map_dir='{write_dirpath}/file_map'
    word_counter_dirpath='{write_dirpath}/word_counter'
    sub_word_counter_dirpath='{write_dirpath}/word_counter/sub_word_counter'
    # sub_word_counter_dirpath='{write_dirpath}/word_counter/sub_word_counter'
    # department_txtpath=os.path.join(write_dirpath,'departments.txt')
    department_txtpath='{write_dirpath}/departments.txt'
    process_args_jsonpath='{write_dirpath}/process_args.json'

    # char_and_span_counter_jsonpath=os.path.join(word_counter_dirpath,'char_and_span_counter.json')
    char_and_span_counter_jsonpath='{write_dirpath}/word_counter/char_and_span_counter.json'
    # department_txtpath=os.path.join(write_dirpath,'departments.txt')

    before_dedup_dirpath='{write_dirpath}/dedup/before_dedup/train'
    after_dedup_dirpath='{write_dirpath}/dedup/after_dedup'

    local_tree_sitter_depend_dir='xxx'
    lpai_tree_sitter_depend_dir='xxx'

    

class FileterCounter(object):
    #multe_dedup_file.sh  shell
    counter_no_import_file=0
    counter_has_import_file=0
    #multi_graph_repo.py
    #相邻行去重
    counter_dedup_neighbour_line=0
    counter_dedup_neighbour_line_file=0

    window_content_end_not_normal=0

    #过滤掉的文件数量
    filter_dir_by_name=0
    filter_file_by_name=0
    counter_import_name_2_path_eq_1=0
    counter_import_name_2_path_gt_1=0

    file_read_content_error=0
    file_alphanum_ratio=0
    file_clean_cross_line=0
    line_max_line_number=0
    line_max_line_length=0
    line_avg_line_length=0
    file_fim_true=0
    file_fim_false=0
    mock_parser=0
    
    file_read_content_error_token_num=0
    file_alphanum_ratio_token_num=0
    file_clean_cross_line_token_num=0
    line_max_line_number_token_num=0
    line_max_line_length_token_num=0
    line_avg_line_length_token_num=0
    file_fim_true_token_num=0
    file_fim_false_token_num=0
    mock_parser_token_num=0
    
    fim_sample_counter=0
    fim_sample_counter_token_num=0

    file_fim_sample_counter=0
    file_fim_sample_counter_token_num=0

    split_by_content_window_size=0
    not_split_by_content_window_size=0

    #函数名重复统计
    funcname_same_in_onefile=0

    #统计函数嵌套解析数量
    has_filepath_2_function_counter=0
    no_filepath_2_function_counter=0
    

    grammar_name_2_counter_dict={}

    @staticmethod
    def counter_info():
        return {
            'counter_no_import_file':FileterCounter.counter_no_import_file,
            'counter_has_import_file':FileterCounter.counter_has_import_file,
            'counter_dedup_neighbour_line':FileterCounter.counter_dedup_neighbour_line,
            'counter_dedup_neighbour_line_file':FileterCounter.counter_dedup_neighbour_line_file,


            'window_content_end_not_normal':FileterCounter.window_content_end_not_normal,
            'file_read_content_error':FileterCounter.file_read_content_error,
            'file_alphanum_ratio':FileterCounter.file_alphanum_ratio,
            'file_clean_cross_line':FileterCounter.file_clean_cross_line,
            'line_max_line_number':FileterCounter.line_max_line_number,
            'line_max_line_length':FileterCounter.line_max_line_length,
            'line_avg_line_length':FileterCounter.line_avg_line_length,
            'file_fim_true':FileterCounter.file_fim_true,
            'file_fim_false':FileterCounter.file_fim_false,
            'mock_parser':FileterCounter.mock_parser,
            'fim_sample_counter':FileterCounter.fim_sample_counter,
            'grammar_name_2_counter_dict':FileterCounter.grammar_name_2_counter_dict,

            'no_filepath_2_function_counter':FileterCounter.no_filepath_2_function_counter,
            'has_filepath_2_function_counter':FileterCounter.has_filepath_2_function_counter,
            
        }
    @staticmethod
    def print():
        print('*************FileterCounter***************')
        for k,v in FileterCounter.counter_info().items():
            print(k,v)
        print('*************grammar_name_2_counter_dict***************')
        for k,v in FileterCounter.grammar_name_2_counter_dict.items():            
            print(k,v)

class PaConstants:
    features=Features({
            'language':Value(dtype="string"),
            'project_path':Value(dtype="string"),
            'path':Value(dtype="string"),
            'imported_files':Value(dtype="string"),
            'src_encoding':Value(dtype="string"),
            'repo_name':Value(dtype="string"),
            'github_id':Value(dtype="string"),
            'content':Value(dtype="string"),
            'bool_testcase':Value(dtype="bool"),
            'parent_2_function_definition_dict':Value(dtype="string"),
            'parent_2_sub_include_func_text_dict':Value(dtype="string"),
            # 'src_encoding:':Value(dtype="string"),
            # 'project_path:':Value(dtype="string"),
            # 'github_id:':Value(dtype="string"),
            # 'path:':Value(dtype="string"),
        })

    dedup_schema=pa.schema([
            ('language',pa.string()),
            ('project_path',pa.string()),
            ('path',pa.string()),
            ('imported_files',pa.string()),
            ('src_encoding',pa.string()),
            ('repo_name',pa.string()),
            ('github_id',pa.string()),
            ('content',pa.string()),
            ('bool_testcase',pa.bool_()),
            ('parent_2_function_definition_dict',pa.string()),
            ('parent_2_sub_include_func_text_dict',pa.string()),
        ])




if __name__=='__main__':
    print(f'project_root_dirpath={project_root_dirpath}')