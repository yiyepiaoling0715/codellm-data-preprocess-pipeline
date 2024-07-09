#!/bin/bash
set -e
echo "parse-sql-data.sh 1111"
. shells/base.sh
  
WRITE_DIR="${1}"
BOOL_UPLOAD="${2}"
mkdir -p "${WRITE_DIR}" || true

# SFT_DIR=${WRITE_DIR}/"sft"



DATASET_PATH_AFTER_DEDUP=${WRITE_DIR}/"sft"
OTHER_DIR=${WRITE_DIR}/"others"
SFT_DIRPATH_FOR_DS=${OTHER_DIR}/dedup/before_dedup
export SFT_DIR="${SFT_DIRPATH_FOR_DS}/train"

mkdir -p "${SFT_DIR}" || true
mkdir -p "${OTHER_DIR}" || true
mkdir -p "${DATASET_PATH_AFTER_DEDUP}" || true


[ ! -d "$SFT_DIR" ] && {
    echo "Please specify sft dir  ${SFT_DIR}"
    exit 1
}

[ ! -d "$OTHER_DIR" ] && {
    echo "Please specify sft dir  ${OTHER_DIR}"
    exit 1
}

echo "**************执行sql 整理数据**************"
python ./pys/parse_sql_data.py "$WRITE_DIR" "$SFT_DIR"  "$OTHER_DIR"

echo "**************数据去重**************"
python -u ./clean/bigcode_dataset/near_deduplication/minhash_deduplication.py \
--dataset $SFT_DIRPATH_FOR_DS \
--cache_dir cache_dir \
--ngram_size 100 \
--threshold 0.8 \
--dataset_path_after_dedup $DATASET_PATH_AFTER_DEDUP/data_reflow.json \
--save_mode save_to_json \
--remove_columns content

echo "**************数据上传lpai**************"
if $BOOL_UPLOAD;then
    python ./pys/upload_for_sft.py $WRITE_DIR
else
    echo "不执行上传"
fi

