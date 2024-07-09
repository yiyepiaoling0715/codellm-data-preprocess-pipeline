"""Here we detect PII: Emails, IP addresses, and keys (SSH/API) and redact/anonymize them
    * we use one regex for emails and one for IP addresses
    * for keys we use detect-secrets tool, which is a combination of multiple plugins (regexes, entropy..)
    * we also add some filters on top of each tool to decrease the number of false positives
This script is adapted from https://github.com/bigscience-workshop/data-preparation/blob/main/preprocessing/training/02_pii/pii_processor.py
"""
import os
import sys
preprocess_dirname=os.path.dirname(os.path.abspath(__file__))
# print('preprocess_dirname=',preprocess_dirname)
sys.path.append(preprocess_dirname)

import argparse
import random
import json
import multiprocessing
from pprint import pformat
from functools import partial
from logger import logger
from datasets.utils.logging import set_verbosity_info
from datasets import load_dataset,load_from_disk
from logger import logger
from pii_detection import scan_pii_batch
from pii_redaction import redact_pii_batch, random_replacements
from utils.manual_sharding import save_manual_shards
from pii_args import parseArgs

def get_check_ds(ds, args):
    if not args.check_all_files:
        ds_checks = ds.filter(
            lambda exs: exs["modified"],
            batched=True,
            batch_size=args.batch_size,
            num_proc=args.num_proc
        )
    else:
        ds_checks = ds
    if not args.check_sampling_size:
        sampling_size = len(ds_checks)
    else:
        sampling_size=args.check_sampling_size
    ##todo 选择一部分数据做检查
    idx_samples = random.sample(range(len(ds_checks)), min(len(ds_checks), sampling_size))
    ds_checks = ds_checks.select(idx_samples)
    return ds_checks

def main(args):
    set_verbosity_info()

    def pprint_args(args):
        message = '\n'.join([f'{k:<30}:   {v}' for k, v in vars(args).items()])
        logger.info('====*****' * 15)
        logger.info(message)
        logger.info('====*****' * 15)
    logger.info(f"** The job is running with the following arguments: ** **** ")
    pprint_args(args=args)

   
    logger.info(f" ===== Loading {args.dataset_name} =====")
    if args.load_local_path:
        ds=load_dataset(path=args.load_local_path,split='train',
                keep_in_memory=True,num_proc=args.num_proc)
        # ds=load_from_disk(dataset_path=args.load_local_path,keep_in_memory=True)
    else:
        ds = load_dataset(args.dataset_name, data_dir=args.subset, split=args.split, 
            use_auth_token=True,keep_in_memory=True)
    try:
        logger.info(f"ds.keys()={ds.features}")
    except AttributeError as e:
        for check_k,check_v in ds.items():
            logger.info(f"AttributeError {check_k}={check_v}")
    if args.text_column != "content":
        ds = ds.rename_column(args.text_column, "content")
    if args.remove_columns_the_stack:
        logger.info("removing extra columns from The Stack")
        columns = ['ext', 'max_stars_repo_head_hexsha', 'max_stars_repo_licenses', 'max_stars_repo_stars_event_min_datetime',\
                  'max_stars_repo_stars_event_max_datetime', 'max_issues_repo_path', 'max_issues_repo_name', 'max_issues_repo_head_hexsha',\
                  'max_issues_repo_licenses', 'max_issues_count', 'max_issues_repo_issues_event_min_datetime', 'max_issues_repo_issues_event_max_datetime', \
                  'max_forks_repo_path', 'max_forks_repo_name', 'max_forks_repo_head_hexsha', \
                  'max_forks_repo_licenses', 'max_forks_count', 'max_forks_repo_forks_event_min_datetime', 'max_forks_repo_forks_event_max_datetime']
        ds = ds.remove_columns(columns) 
        logger.info(f"New dataset fomat: {ds}")
    # add id column to dataset
    logger.info(f" ===== Adding an index column =====")
    ds = ds.add_column("index", list(range(len(ds))))

    logger.info(f" ===== Applying PII detection =====")
    ds_pii = ds.map(
        scan_pii_batch, batched=True, batch_size=args.batch_size, num_proc=args.num_proc, 
        # keep_in_memory=True
        load_from_cache_file=True
    )
    logger.info(f"Dataset info after PII detection:\n{ds_pii}")
    logger.info(f"Number of samples that contained PII: {sum(ds_pii['has_secrets'])}")
    logger.info(f"Total number of secrets found: {sum(ds_pii['number_secrets'])}")


    # redact PII in the dataset
    ## 读取 replacement 值,并对 content中的数据进行替换
    if not args.no_redaction:
        logger.info(f" ===== Applying PII redaction =====")
        random.seed(args.seed)

        # we use random replacements by default
        if args.load_replacements:
            pro_rootpath=os.path.dirname(os.path.abspath(__file__))
            replace_jsonpath=os.path.join(pro_rootpath,"replacements.json")
            with open(replace_jsonpath, "r") as f:
            # with open("replacements.json", "r") as f:
                replacements = json.load(f)
        else:
            replacements = random_replacements()
            with open("random_replacements.json", "w") as f:
                json.dump(replacements, f)
        logger.info(f"Using the following replacements:\n{pformat(replacements)}")
        ds_pii = ds_pii.map(
            partial(redact_pii_batch, replacements=replacements, add_references=args.add_reference_text),
            batched=True,
            batch_size=args.batch_size,
            num_proc=args.num_proc,
            # keep_in_memory=True
            load_from_cache_file=True
        )
        logger.info(f"Dataset info after PII redaction:\n{ds_pii}")

        # check the dataset
        logger.info(f" ===== Checking {args.check_sampling_size} samples from those modified in the dataset =====")
        #获取一部分可检查的数据
        ds_checks = get_check_ds(ds_pii, args)

        # save checksredact_pii_batch dataset
        if len(ds_checks) == 0:
            logger.info("Dataset was empty. Not saving anything.")
        else:
            logger.info(f"Checks dataset info {ds_checks}")
            if args.save_mode_checks == "hub":
                logger.info(f"Pushing the checks dataset to the Hub as {args.target_dataset}_checks")
                ds_checks.push_to_hub(args.target_dataset + "_checks")
            
            elif args.save_mode_checks == "local":
                logger.info(f"Saving the checks dataset to disk")
                ds_checks.save_to_disk(args.save_path_disk + "_checks")
            
            elif args.save_mode_checks == "manual_shards":
                logger.info(f"Saving the checks dataset in manual shards")
                save_manual_shards(ds_checks, user=args.hub_username, remote_dataset_repo=args.target_dataset + "_checks")
            
        logger.info("Removing columns that are not needed for the final dataset")
        columns = ["content", "modified", "secrets", "has_secrets", "number_secrets"]
        if args.add_reference_text:
            columns.append("references")
        ds_pii = ds_pii.remove_columns(columns) 
        ds_pii = ds_pii.rename_column("new_content", "content")
        logger.info(f"Dataset info after removing columns:\n{ds_pii}")
    
    # save the final dataset
    if args.save_mode == "hub":
        logger.info(f" ===== Pushing the dataset to the Hub as: {args.target_dataset} =====")
        ds_pii.push_to_hub(args.target_dataset)

    elif args.save_mode == "local":
        logger.info(f" ===== Saving the dataset to disk =====")
        logger.info(f'args.save_mode={args.save_mode},args.save_path_disk={args.save_path_disk}')
        save_to_disk_dir=os.path.join(args.save_path_disk,'train')
        ds_pii.save_to_disk(save_to_disk_dir,num_proc=args.num_proc)

    elif args.save_mode == "manual_shards":
        logger.info(f" ===== Saving the dataset in manual shards =====")
        save_manual_shards(ds_pii, user=args.hub_username, remote_dataset_repo=args.target_dataset)
    
    logger.info(f" ===== Dataset saved successfully =====")


# def domain_filter():
#     """
#         按照拓扑图组织content,构建dataset
#         利用各个filter策略
#     """
    
#     ds_pii = ds.map(
#         scan_pii_batch, batched=True, batch_size=args.batch_size, num_proc=args.num_proc, 
#         # load_from_cache_file=False
#         keep_in_memory=True
#         )
#     ##将敏感数据替换为一些 不重要的值
#     if args.load_replacements:
#             with open("replacements.json", "r") as f:
#                 replacements = json.load(f)
#     else:
#         replacements = random_replacements()
#         with open("random_replacements.json", "w") as f:
#             json.dump(replacements, f)
#     logging.info(f"Using the following replacements:\n{pformat(replacements)}")
#     ds_pii = ds_pii.map(
#         partial(redact_pii_batch, replacements=replacements, add_references=args.add_reference_text),
#         batched=True,
#         batch_size=args.batch_size,
#         num_proc=args.num_proc,
#         load_from_cache_file=False
#     )




if __name__ == "__main__":
    args = parseArgs()
    main(args)
