CURRENT_DIR=$(cd `dirname $0`; pwd)
echo "CURRENT_DIR=$CURRENT_DIR"
workdir=$(dirname "$CURRENT_DIR")
echo "workdir=$workdir"
export PYTHONPATH="$workdir:$PYTHONPATH"



# 定义函数
get_last_and_third_last_elements() {
    local IFS='/'           # 设置局部变量 IFS (内部字段分隔符) 为 '/'
    read -ra ADDR <<< "$1"  # 将输入参数按照 '/' 切分，并存入数组 ADDR

    local len=${#ADDR[@]}   # 获取数组元素的数量
    local last_element=${ADDR[-1]}      # 获取倒数第一个元素
    local third_last_element=${ADDR[-3]} # 获取倒数第三个元素

    # 判断元素是否存在，如果是越界情况设为空
    last_element=${last_element:-}
    third_last_element=${third_last_element:-}

    # 返回倒数第一个和倒数第三个元素
    echo "$third_last_element"
    echo "$last_element"
}



create_read_write_of_repos_path(){
    if [ "$1" = "LOCAL" ];then
    
        base_src=xxx
        output_dirpath_of_graph=xxxxxx
        #for pipeline debug end


        export src_dirpath_list=$base_src
    elif [ "$1" = "LPAI" ];then
        # # # # # #lpai
        # export base_src=/lpai/volumes/sc-ep-ulan/llm_data/0516
        export base_src=xxx
        export dirpath_1=xxx
        export dirpath_2=xxx
    
        export src_dirpath_list="$dirpath_1,dirpath_2"

        DATE_STR="${data-$(date +%Y%m%d)}"
        output_dirpath_of_graph=/lpai/volumes/sc-ep-lf/llm_data_clean/${DATE_STR}/repo_graph_repos_with_calc
    elif [ "$1" = "LPAI_TEST" ];then
        export base_src=/lpai/volumes/sc-ep-lf/test_llm_data/0620
        export lpai_chekong_os_dirpath="${base_src}/datasets-chekong-os/data"
        src_dirpath_list="$lpai_chekong_os_dirpath"
        DATE_STR="${data-$(date +%Y%m%d)}"
        output_dirpath_of_graph=/xxx

    else
        exit 0
    fi
    # mkdir -p $write_dirpath
    echo "$src_dirpath_list"
    echo "$output_dirpath_of_graph"
}