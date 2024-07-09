
python main.py \
--dataset_name bigcode/the-stack-smol \
--subset data/python \
--batch_size 1000 \
--num_proc 64 \
--target_dataset stack-smol-python-pii \
--load_replacements True \
--save_mode_checks local \
--save_mode local \
--save_path_disk  /xxx