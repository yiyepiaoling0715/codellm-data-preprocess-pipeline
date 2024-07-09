
import argparse

def get_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bool_calc_feature", action="store_true", default=None)
    parser.add_argument("--bool_no_parser_with_normal", action="store_true", default=None)
    parser.add_argument("--write_dirpath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--before_dedup_dirpath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--filepath_2_function_info_dict_jsonpath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--function_2_filepath_list_dict_jsonpath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--filepath_2_filepath_list_dict_jsonpath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--root_dir_of_cpp_compile_abspath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--testcase_dataset_jsonpath", type=str, default='/lpai/volumes/sc-ep-ulan/tmp/repo_graph_repos')
    parser.add_argument("--src_dirpath_list", type=str, default=None)
    parser.add_argument("--dataset_path_after_dedup", type=str, default=None)
    parser.add_argument("--alphanum_ratio", type=float, default=0.25)
    parser.add_argument("--line_max", type=float, default=1000)
    parser.add_argument("--line_mean", type=float, default=100)
    parser.add_argument("--max_line_number", type=int, default=50000)
    args=parser.parse_args()
    return args

