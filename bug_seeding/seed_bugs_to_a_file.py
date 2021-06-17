"""

Created on 01-April-2020
@author Jibesh Patra

"""
from bug_seeding_approaches.SemSeed.SemSeedBugs import SemSeedBugs
import utils.static_analysis_utils as static_analysis_utils
import utils.fileutils as fs
import random
from tqdm import tqdm
from pathlib import Path
from typing import List
import os
import jsbeautifier

random.seed(a=42)


def seed_bugs_to_a_file_multiprocessing(args):
    """
    The multiprocessing wrapper of seed_bugs_to_a_file function
    :param args:
    :return:
    """
    file, bug_seeding_patterns, K_most_frequent_identifiers, K_most_frequent_literals, MAX_TRIES_TO_SEED_BUGS, out_dir = args
    return seed_bugs_to_a_file(file, bug_seeding_patterns, K_most_frequent_identifiers, K_most_frequent_literals,
                               MAX_TRIES_TO_SEED_BUGS, out_dir)


def seed_bugs_to_a_file(file: str,
                        bug_seeding_patterns: List,
                        K_most_frequent_identifiers: List,
                        K_most_frequent_literals: List,
                        MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS: int,
                        out_dir: str) -> int:
    """
    Given a file seed bugs to it. The expected file is a JSON file rather than a JS file. It is expected
    that the input JS file has been analysed before and a corresponding JSON file has been createdl
    :param file: the corresponding JSON file of the JS file where bugs need to be seeded
    :param bug_seeding_patterns:
    :param K_most_frequent_identifiers:
    :param K_most_frequent_literals:
    :param MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS:
    :param out_dir: A path where the mutate code will be written
    :return: The count of bugs that could be seeded to the file
    """
    num_of_locations_that_could_be_mutated = 0

    target_js_file_analysed = fs.read_json_file(file)
    if len(target_js_file_analysed) == 0:  # The static analysis could not finish properly
        return num_of_locations_that_could_be_mutated
    possible_bug_seeding_locations = target_js_file_analysed['nodes']

    # We do not want to select the first 'n' locations and try to seed bugs. Rather we randomly
    # choose 'n' locations
    random.shuffle(possible_bug_seeding_locations)
    if MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS > 1:
        possible_bug_seeding_locations = possible_bug_seeding_locations[:MAX_LOCATIONS_TO_TRY_TO_SEED_BUGS]

    # Get Identifiers and Literals available for selection in different scope
    identifiers_in_different_scopes = static_analysis_utils.get_tokens_from_different_scopes(
        analysed_file=target_js_file_analysed,
        kind='identifier',
        k_most_frequent=K_most_frequent_identifiers)
    literals_in_different_scopes = static_analysis_utils.get_tokens_from_different_scopes(
        analysed_file=target_js_file_analysed,
        kind='literal',
        k_most_frequent=K_most_frequent_literals)

    file_name = Path(file).name
    # Go through each seeding pattern available from the bug seeding patterns
    for seeding_pattern in tqdm(bug_seeding_patterns, position=1, ncols=100, ascii=" #",
                                desc='Trying to apply pattern',
                                postfix={'file': file_name}):
        # For each location in the file, try to seed a bug
        for target_location in possible_bug_seeding_locations:
            # ------------------------ SemSeed -----------------------------------------
            bug_seeding = SemSeedBugs(bug_seeding_pattern=seeding_pattern,
                                      target_location=target_location,
                                      file_path=target_js_file_analysed['file_path'],
                                      similarity_threshold=0.3,
                                      K=1,
                                      available_identifiers=identifiers_in_different_scopes,
                                      available_literals=literals_in_different_scopes,
                                      scope_of_selection='top_K')

            # Check if the seeding pattern and the target locations match
            if bug_seeding.is_matching_token_sequence():

                # The mutated token sequences is only the 'mutated' target location token sequence
                # We may get multiple sequences based on K. If K=2 and there is only one
                # unbound token, we get 2 sequences
                mutated_token_sequences = bug_seeding.apply_pattern()
                if len(mutated_token_sequences) > 0:
                    num_of_locations_that_could_be_mutated += 1

                    for ms, mutated_sequence in enumerate(mutated_token_sequences):
                        token_sequence_after_seeding_bug = bug_seeding.replace_target_with_mutated_token_sequence(
                            token_list=target_js_file_analysed['tokenList'],
                            token_range_list=target_js_file_analysed['tokenRangesList'],
                            mutated_token_sequence=mutated_sequence)

                        bug_seeding.bug_metadata['target_token_sequence-Buggy'] = mutated_sequence
                        bug_seeding.bug_metadata['token_sequence_abstraction-Buggy'] = seeding_pattern['buggy']
                        bug_seeding.bug_metadata['num_of_available_identifiers_to_choose_from'] = len(
                            bug_seeding.identifiers_available_for_selecting_unbound_token)
                        bug_seeding.bug_metadata['num_of_available_literals_to_choose_from'] = len(
                            bug_seeding.literals_available_for_selecting_unbound_token)
                        bug_seeding.bug_metadata['seeding_pattern_url'] = seeding_pattern['url']

                        # Simply joining the token list with a space
                        mutated_code = ' '.join(token_sequence_after_seeding_bug)

                        # Write the output code & metadata about the bug seed
                        out_file_name = file_name.replace('.json',
                                                          f'_SEMSEED_MUTATED_{num_of_locations_that_could_be_mutated}.js')
                        out_file_path = os.path.join(out_dir, out_file_name)
                        if fs.pathExists(out_file_path):
                            out_file_path = out_file_path.replace('.js',
                                                                  f'_{str(random.randint(0, 10000))}_{["a", "b", "c", "d"][random.randint(0, 3)]}.js')
                        try:
                            # Remember, this does not check for Syntax Errors in the generated JS code. This needs to be
                            # done separately
                            mutated_code = jsbeautifier.beautify(mutated_code, {
                                "indent_empty_lines": False,
                                "break_chained_methods": False,
                                "space_after_anon_function": False,
                                "space_in_paren": False
                            })
                            fs.writeFile(data=mutated_code, file_path=out_file_path)
                        except Exception as e:
                            tqdm.write(f'ERROR: Could not seed bugs to {file_name} because {e}')
                            bug_seeding.bug_metadata['error'] = str(e)
                        finally:
                            fs.writeJSONFile(data=bug_seeding.bug_metadata, file_path=out_file_path + 'on')
                    else:
                        pass

    return num_of_locations_that_could_be_mutated
