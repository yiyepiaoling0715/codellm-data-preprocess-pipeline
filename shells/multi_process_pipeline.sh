CURRENT_DIR=$(cd `dirname $0`; pwd)
echo "CURRENT_DIR=$CURRENT_DIR"
workdir=$(dirname "$CURRENT_DIR")
. base.sh
export PYTHONPATH="$workdir:$PYTHONPATH"
export WORK_ENV=LPAI
# export WORK_ENV=LOCAL


readarray -t elements < <(create_read_write_of_repos_path ${WORK_ENV}) # 调用函数
export src_dirpath_list=${elements[0]}
output_dirpath_of_graph=${elements[1]}
output_dirpath_of_pii="${output_dirpath_of_graph}"_pii
output_dirpath_of_pii_check="${output_dirpath_of_graph}"_checks
dataset_path_after_dedup=${output_dirpath_of_graph}/dedup/after_dedup
before_dedup_dirpath=$output_dirpath_of_graph/dedup/before_dedup
dataset_path_after_dedup=$output_dirpath_of_graph/dedup/after_dedup/train
dst_json_dirpath_of_graph=$output_dirpath_of_graph/json
cache_dir_minhash_deduplication=$output_dirpath_of_graph/cache/minhash_deduplication


rm -rf $output_dirpath_of_graph

echo "The read path is:"
echo "${src_dirpath_list}"
echo "The write path is:"
echo "${output_dirpath_of_graph}"
mkdir -p $output_dirpath_of_graph
mkdir -p $before_dedup_dirpath
mkdir -p $dataset_path_after_dedup
mkdir -p $output_dirpath_of_pii
mkdir -p $output_dirpath_of_pii_check
mkdir -p $output_dirpath_of_graph
mkdir -p $cache_dir_minhash_deduplication

echo "output_dirpath_of_pii=$output_dirpath_of_pii"
echo "output_dirpath_of_pii_check=$output_dirpath_of_pii_check"
echo "dst_json_dirpath_of_graph=$dst_json_dirpath_of_graph"
echo "before_dedup_dirpath=$before_dedup_dirpath"
echo "dataset_path_after_dedup=$dataset_path_after_dedup"

# nohup_log_dirpath=$workdir/shells/nohups
# nohup_log_dirpath=$LOG_DIR
nohup_log_dirpath=/tmp/output/logs/logs
nohup_after_dedup_log_path=$nohup_log_dirpath/nohup_after_dedup.log
nohup_repo_graph_log_path=$nohup_log_dirpath/nohup_repo_graphs.log
nohup_pii_log_path=$nohup_log_dirpath/nohup_pii.log
export nohup_pii_logger_path=$nohup_log_dirpath/pii.log
nohup_multi_dedup_file_log_path=$nohup_log_dirpath/nohup_multi_dedup_file.log
mkdir -p $nohup_log_dirpath



depend_parser_dirpath=${output_dirpath_of_graph}/depend_parser
mkdir -p $depend_parser_dirpath
filepath_2_function_info_dict_jsonpath=$depend_parser_dirpath/filepath_2_function_info_dict.json
function_2_filepath_list_dict_jsonpath=$depend_parser_dirpath/function_2_filepath_list_dict.json
filepath_2_filepath_list_dict_jsonpath=$depend_parser_dirpath/filepath_2_filepath_list_dict.json


#src_dirpath_list  根目录列表，靠,切分，不同人物的原始的代码仓库在每个根目录下面

echo "开始执行multi_dedup_file...,整理为可去重文件形式"
echo -e "nohup_multi_dedup_file_log_path=\n$nohup_multi_dedup_file_log_path"
python ../repo_graphs/multi_dedup_file.py \
--bool_calc_feature \
--src_dirpath_list $src_dirpath_list \
--write_dirpath $output_dirpath_of_graph \
--filepath_2_function_info_dict_jsonpath $filepath_2_function_info_dict_jsonpath \
--function_2_filepath_list_dict_jsonpath $function_2_filepath_list_dict_jsonpath \
--filepath_2_filepath_list_dict_jsonpath $filepath_2_filepath_list_dict_jsonpath \
>$nohup_multi_dedup_file_log_path 2>&1


echo "开始执行minhash_deduplication...,文件级别清洗去重"
echo -e "nohup_after_dedup_log_path=\n$nohup_after_dedup_log_path"
python -u ../clean/bigcode_dataset/near_deduplication/minhash_deduplication.py \
--dataset $before_dedup_dirpath \
--cache_dir cache_dir_minhash_deduplication \
--ngram_size 50 \
--threshold 0.8 \
--dataset_path_after_dedup $dataset_path_after_dedup \
>$nohup_after_dedup_log_path 2>&1


echo "开始执行repo_graphs.py...,清洗整理为图文件形式"
echo -e "nohup_repo_graph_log_path=\n$nohup_repo_graph_log_path"

python -u $workdir/repo_graphs/multi_graph_repo.py \
--bool_calc_feature \
--src_dirpath_list $src_dirpath_list \
--dataset_path_after_dedup $dataset_path_after_dedup \
--write_dirpath $output_dirpath_of_graph \
>$nohup_repo_graph_log_path 2>&1


echo "开始执行pii,脱敏处理"
echo -e "nohup_pii_log_path=\n$nohup_pii_log_path"

python -u $workdir/clean/bigcode_dataset/pii/main_process.py \
--load_local_path $dst_json_dirpath_of_graph \
--batch_size 1000 \
--load_replacements True \
--save_mode_checks local \
--save_mode local \
--save_path_disk  $output_dirpath_of_pii  \
>$nohup_pii_log_path 2>&1



echo "pipeline 执行处理完毕,退出所有程序"





