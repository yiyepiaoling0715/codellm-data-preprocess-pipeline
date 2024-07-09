

# export WORK_ENV=LOCAL
export WORK_ENV=LPAI_TEST
. base.sh

mkdir -p nohups

readarray -t elements < <(create_read_write_of_repos_path "$WORK_ENV") # 调用函数
export src_dirpath_list=${elements[0]}
output_dirpath_of_graph=${elements[1]}

before_dedup_dirpath=$output_dirpath_of_graph/dedup/before_dedup
filepath_2_function_info_dict_jsonpath=$output_dirpath_of_graph/depend_parser/filepath_2_function_info_dict.json
function_2_filepath_list_dict_jsonpath=$output_dirpath_of_graph/depend_parser/function_2_filepath_list_dict.json
filepath_2_filepath_list_dict_jsonpath=$output_dirpath_of_graph/depend_parser/filepath_2_filepath_list_dict.json
export testcase_dataset_jsonpath=$output_dirpath_of_graph/depend_parser/testcase_dataset.json
echo "testcase_dataset_jsonpath=$testcase_dataset_jsonpath"
python  ../testcase/main_process.py \
--before_dedup_dirpath $before_dedup_dirpath \
--filepath_2_function_info_dict_jsonpath $filepath_2_function_info_dict_jsonpath \
--function_2_filepath_list_dict_jsonpath $function_2_filepath_list_dict_jsonpath \
--filepath_2_filepath_list_dict_jsonpath $filepath_2_filepath_list_dict_jsonpath \
--testcase_dataset_jsonpath $testcase_dataset_jsonpath \
--src_dirpath_list $src_dirpath_list \
> nohups/nohup_testcase.log 2>&1 &
echo "logpath=    nohups/nohup_testcase.log"
echo "exit testcase_debug.sh"

