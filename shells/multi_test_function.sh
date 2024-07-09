
CURRENT_DIR=$(cd `dirname $0`; pwd)
echo "CURRENT_DIR=$CURRENT_DIR"
workdir=$(dirname "$CURRENT_DIR")

export PYTHONPATH="$workdir:$PYTHONPATH"
# export WORK_ENV=LOCAL
export WORK_ENV=LPAI_TEST
echo "on base.sh WORK_ENV=$WORK_ENV"
. base.sh
echo "under base.sh WORK_ENV=$WORK_ENV"


readarray -t elements < <(create_read_write_of_repos_path "$WORK_ENV") # 调用函数
export src_dirpath_list=${elements[0]}
output_dirpath_of_graph=${elements[1]}
output_dirpath_of_pii="${output_dirpath_of_graph}"_pii
output_dirpath_of_pii_check="${output_dirpath_of_graph}"_checks
echo "The read path is:"
echo "${src_dirpath_list}"
echo "The write path is:"
echo "${output_dirpath_of_graph}"
mkdir -p $output_dirpath_of_graph
mkdir -p $output_dirpath_of_pii
mkdir -p $output_dirpath_of_pii_check

dataset_path_before_dedup=${output_dirpath_of_graph}/dedup/before_dedup
dataset_path_after_dedup=${output_dirpath_of_graph}/dedup/after_dedup
mkdir -p $dataset_path_after_dedup

depend_parser_dirpath=${output_dirpath_of_graph}/depend_parser
mkdir -p $depend_parser_dirpath
filepath_2_function_info_dict_jsonpath=$depend_parser_dirpath/filepath_2_function_info_dict.json
function_2_filepath_list_dict_jsonpath=$depend_parser_dirpath/function_2_filepath_list_dict.json
filepath_2_filepath_list_dict_jsonpath=$depend_parser_dirpath/filepath_2_filepath_list_dict.json
rood_dir_of_cpp_compile_abspath=/xxx
# workdir=$(dirname $(dirname "$PWD"))
# workdir=$(dirname $(dirname "$CURRENT_DIR"))
echo "workdir=$workdir"
nohup_log_dirpath=$workdir/shells/nohups
nohup_before_dedup_log_path=$nohup_log_dirpath/nohup_before_dedup.log
nohup_after_dedup_log_path=$nohup_log_dirpath/nohup_after_dedup.log
# nohup_pii_log_path=$nohup_log_dirpath/nohup_pii.log
mkdir -p $nohup_log_dirpath

# dst_json_dirpath_of_graph=$output_dirpath_of_graph/json
# echo "dst_json_dirpath_of_graph=$dst_json_dirpath_of_graph"
echo "测试用例模式,解析{文件:函数}映射关系"
echo "开始执行multi_dedup_file...,整理为可去重文件形式"

# python -u ../repo_graphs/multi_dedup_file.py \
# --bool_calc_feature \
# --src_dirpath_list $src_dirpath_list \
# --write_dirpath $output_dirpath_of_graph \
# >$nohup_before_dedup_log_path 2>&1

python -u ../repo_graphs/multi_dedup_file.py \
--bool_calc_feature \
--src_dirpath_list $src_dirpath_list \
--write_dirpath $output_dirpath_of_graph \
--filepath_2_function_info_dict_jsonpath $filepath_2_function_info_dict_jsonpath \
--function_2_filepath_list_dict_jsonpath $function_2_filepath_list_dict_jsonpath \
--filepath_2_filepath_list_dict_jsonpath $filepath_2_filepath_list_dict_jsonpath \
--rood_dir_of_cpp_compile_abspath $rood_dir_of_cpp_compile_abspath \
>$nohup_before_dedup_log_path 2>&1

echo -e "nohup_before_dedup_log_path=\n${nohup_before_dedup_log_path}"

