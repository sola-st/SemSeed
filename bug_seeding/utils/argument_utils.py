"""

Created on 24-March-2020
@author Jibesh Patra

"""
from argparse import ArgumentParser
from utils.fileutils import create_dir_list_if_not_present
from typing import Tuple


def read_arguments(parser: ArgumentParser) -> Tuple:
    parser = add_arguments_to_parser(parser)
    args = parser.parse_args()
    create_dir_list_if_not_present([args.out_dir, args.working_dir, args.stats_dir])
    return args.in_dir, args.out_dir, args.working_dir, args.stats_dir, args.bug_seeding_patterns, args.K_freq_idf, args.K_freq_lit


def add_arguments_to_parser(parser: ArgumentParser) -> ArgumentParser:
    parser.add_argument(
        '--in_dir',
        type=str,
        default='benchmarks/data',
        help='The directory containing JS files where bugs may be seeded'
    )
    parser.add_argument(
        '--out_dir',
        type=str,
        default='benchmarks/js_benchmark_seeded_bugs',
        help='The directory where the bug seeded files will written'
    )
    parser.add_argument(
        '--working_dir',
        type=str,
        default='benchmarks/js_benchmark_working_dir',
        help='The directory where intermediate results will be written'
    )
    parser.add_argument(
        '--stats_dir',
        type=str,
        default='benchmarks/js_benchmark_stats',
        help='The directory where statistics about bug seeding will be written'
    )
    parser.add_argument(
        '--bug_seeding_patterns',
        type=str,
        default='benchmarks/bug_seeding_patterns_for_semantic_seeding.json',
        help='The path to a file that contains the change patterns'
    )

    parser.add_argument(
        '--K_freq_idf',
        type=str,
        default='benchmarks/topK_identifiers_in_training_commits.json',
        help='K most frequent Identifier'
    )

    parser.add_argument(
        '--K_freq_lit',
        type=str,
        default='benchmarks/topK_literals_in_training_commits.json',
        help='K most frequent Literal'
    )

    return parser
