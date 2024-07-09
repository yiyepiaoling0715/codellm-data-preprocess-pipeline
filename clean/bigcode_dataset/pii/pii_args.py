import argparse
import os
import multiprocessing


def parseArgs():
    parser = argparse.ArgumentParser(description="PII detection and redaction")
    parser.add_argument(
        "--dataset_name",
        default="bigcode/pii-for-code",
        type=str,
        help="HF repo name/path of the dataset.",
    )
    parser.add_argument(
        "--subset",
        default="data/",
        type=str,
        help="Data subset to use.",
    )
    parser.add_argument(
        "--text_column",
        default="content",
        type=str,
        help="Text column to use, if will be renamed to content",
    )
    parser.add_argument(
        "--split",
        default="train",
        type=str,
        help="Dataset split to process",
    )
    parser.add_argument(
        "--batch_size",
        default=100,
        type=int,
        help="Batch size for the PII detection/redaction",
    )
    parser.add_argument(
        "--seed",
        default=0,
        type=int,
        help="Seed for random",
    )
    parser.add_argument(
        "--num_proc",
        default=multiprocessing.cpu_count(),
        type=int,
        help="Number of processes to use for the PII detection/redaction",
    )
    parser.add_argument(
        "--no_redaction",
        action="store_true",
        help="If set, we don't perform redaction",
    )
    parser.add_argument(
        "--load_replacements",
        default=True,
        help="If set, we load the replacements from file replacements.json",
    )
    parser.add_argument(
        "--add_reference_text",
        default=True,
        type=bool,
        help="If True we add the reference text with PII between delimiters \
        in the redacted text -used for visualization-",
    )
    parser.add_argument(
        "--check_all_files",
        action="store_true",
        help="If set, we check all files, not only the ones that contain PII",
    )
    parser.add_argument(
        "--check_sampling_size",
        # default=1000,
        default=100,
        type=int,
        help="Number of samples to check for PII",
    )
    # for saving the dataset: either push to HF or save locally with datasets or save manual shards
    parser.add_argument(
        "--save_mode",
        # default="manual_shards",
        default="local",
        type=str,
        choices=["hub", "local", "manual_shards"],
        help="How to save the dataset",
    )
    parser.add_argument(
        "--save_mode_checks",
        default="local",
        type=str,
        choices=["hub", "local", "manual_shards"],
        help="How to save the  checks dataset",
    )
    # add argument for name of dataset on the hub
    parser.add_argument(
        "--target_dataset",
        default="bigcode-pii-pjj",
        type=str,
        help="HF repo name of the target dataset in save_mode=hub.",
    )
    parser.add_argument(
        "--hub_username",
        default="loubnabnl",
        type=str,
        help="Username for the hub",
    )
    parser.add_argument(
        "--save_path_disk",
        default=None,
        type=str,
        help="Path to save the dataset on disk in save_mode=local.",
    )
    parser.add_argument(
        # TODO: investigate issue to remove this arg
        "--remove_columns_the_stack",
        # default=True,
        default=False,
        type=bool,
        help="The Stack v1.1 has many columns and this can cause an issue during processing of large subsets.",
    )
    parser.add_argument(
        "--load_local_path",
        default=None,
        type=str,
        help="HF repo name/path of the dataset.",
    )

    parser.add_argument(
        "--project_dirpath",
        default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        type=str,
        help="HF repo name/path of the dataset.",
    )
    # add
    # add an option of evaluating the pipeline on the PII benchmark we built

    return parser.parse_args()

