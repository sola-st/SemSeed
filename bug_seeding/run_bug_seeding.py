"""

Created on 17-March-2020
@author Jibesh Patra

The main file from where all experiments are run
"""
import argparse
import utils.fileutils as fs
from utils.argument_utils import read_arguments
from utils.prepare_for_seeding_bug import prepare_dir_for_seeding_bugs
from utils.bug_seeding_pattern_utils import find_wrong_operand_in_binary_op_patterns, \
    get_only_idf_lit_containing_patterns
import os
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from seed_bugs_to_a_file import seed_bugs_to_a_file, seed_bugs_to_a_file_multiprocessing
import numpy as np


def select_particular_type_of_seeding_pattern(bug_seeding_patterns):
    # Select only 'Wrong Binary Operand' patterns
    # bug_seeding_patterns = find_wrong_operand_in_binary_op_patterns(bug_seeding_patterns)

    # Select only 'Wrong Assignments' patterns
    # bug_seeding_patterns = fs.read_json_file('benchmarks/bug_seeding_patterns_wrong_assignment.json')
    return bug_seeding_patterns


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='python run_bug_seeding.py',
        description="Provide the proper directories where bugs may be seeded",
        epilog="You must provide directories"
    )
    in_dir, out_dir, working_dir, stats_dir, bug_seeding_patterns, k_freq_idf, k_freq_lit = read_arguments(parser)

    # print("Sampling files for using as target to seed bugs")
    # fs.sample_from_zip(zip_file_path='benchmarks/data.zip', out_dir=in_dir, file_extension_to_sample='.js',
    #                    required_number_of_files=100)

    # Read bug seeding patterns
    all_bug_seeding_patterns = fs.read_json_file(bug_seeding_patterns)
    all_bug_seeding_patterns = get_only_idf_lit_containing_patterns(all_bug_seeding_patterns)
    print(f"Complete bug seeding patterns = {len(all_bug_seeding_patterns)}")
    l_len = len(all_bug_seeding_patterns) * 80 // 100
    tr_patterns, val_patterns = all_bug_seeding_patterns[:l_len], all_bug_seeding_patterns[l_len:]
    print(
        f'Training patterns are {len(tr_patterns)} and validation are {len(val_patterns)}. We only use training patterns for bug seeding')
    bug_seeding_patterns = tr_patterns

    bug_seeding_patterns = select_particular_type_of_seeding_pattern(bug_seeding_patterns=bug_seeding_patterns)
    print("There are {} bug seeding patterns".format(len(bug_seeding_patterns)))

    # More intermediate directories needed
    static_analysis_out_dir = os.path.join(working_dir, '__TEMP__target_js_file_nodes')

    print("Preparing for bug seeding")
    prepare_dir_for_seeding_bugs(target_js_dir=in_dir,
                                 abstracted_out_dir=static_analysis_out_dir, num_of_files=-1)

    # Maximum number of tries to seed bugs per file. We could be always successful and seed 10 bugs or 0
    MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS = -1  # If -1 then try to seed everywhere
    actual_mutations_in_each_file = []

    # Now seed bugs
    K_most_frequent_identifiers = fs.read_json_file(k_freq_idf)
    K_most_frequent_literals = fs.read_json_file(k_freq_lit)
    analysed_files = fs.go_through_dir(directory=static_analysis_out_dir, filter_file_extension='.json')

    args_for_files = [
        (file, bug_seeding_patterns, K_most_frequent_identifiers, K_most_frequent_literals,
         MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS, out_dir) for
        file in analysed_files]

    # Multiprocessing only on machine with many CPUs
    if cpu_count() > 4:
        with Pool(processes=cpu_count()) as p:
            with tqdm(total=len(analysed_files)) as pbar:
                pbar.set_description_str(
                    desc="Seeding bugs to files ", refresh=False)
                for i, successful_mutations in tqdm(
                        enumerate(p.imap_unordered(seed_bugs_to_a_file_multiprocessing, args_for_files, chunksize=1)),
                        position=0):
                    actual_mutations_in_each_file.append(successful_mutations)
                    pbar.update()
                p.close()
                p.join()
    else:
        # Non multiprocessing
        for file in tqdm(analysed_files, desc='Seeding bugs to files', position=0, postfix={'approach': 'SemSeed'}):
            successful_mutations = seed_bugs_to_a_file(file, bug_seeding_patterns, K_most_frequent_identifiers,
                                                       K_most_frequent_literals,
                                                       MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS, out_dir)
            actual_mutations_in_each_file.append(successful_mutations)

    print("\n *** Bugs could be seeded in {}/{} files output directory is '{}' ***".format(
        np.count_nonzero(actual_mutations_in_each_file),
        len(analysed_files), out_dir))
