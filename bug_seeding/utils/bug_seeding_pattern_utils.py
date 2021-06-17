"""

Created on 02-April-2020
@author Jibesh Patra

Given all change patterns do stuffs with them

"""
from typing import List, Tuple
import utils.fileutils as fs
import re
import pandas as pd


def get_only_idf_lit_containing_patterns(all_changes):
    """
    It is possible that every bug-fix pattern can not be used to seed bugs.
    We filter some of them here. For example:
        * we may filter very long change patterns (although we do it once while aggregating data from MongoDB)
        * we may select only those chage patterns that has atleast 'N' frequency
    """
    filtered_change_patterns = []

    # # ----------------------- Filtering number of tokens -------------------------
    # max_number_of_tokens = 10
    # for change_pattern in self.all_training_change_patterns:
    #     print('\n\n \t *** ***  Selecting only change patterns having total {} tokens *** ***'.format(max_number_of_tokens*2))
    #     if len(change_pattern['fix']) <= max_number_of_tokens and len(change_pattern['buggy']) <= max_number_of_tokens:
    #         filtered_change_patterns.append(change_pattern)

    # ----------------------- Filtering based on the frequency of the change patterns -----------------
    # min_frequency = 4
    # print('\n \t *** ***  Filtering only change patterns having minimum frequency  {} *** ***\n'.format(min_frequency))
    # mapping_of_change_patterns = SeedBugs._str_mapping_change_pattern_to_change(
    #     all_changes)

    # for mapped_seq in mapping_of_change_patterns:
    #     if len(mapping_of_change_patterns[mapped_seq]) >= min_frequency:
    #         filtered_change_patterns.extend(
    #             mapping_of_change_patterns[mapped_seq])

    # print("\tTotal {} change patterns and {} filtered change patterns ".format(
    #     len(mapping_of_change_patterns), len(filtered_change_patterns)))

    # ------------------- Remove those change patterns that does not contain any Identifiers/Literals ------------
    for t in all_changes:
        # If the change pattern contains at-least one Identifier/Literal, we use that.
        # Else the change pattern is discarded
        if 'Idf_' in ' '.join(t['fix']) or 'Idf_' in ' '.join(t['buggy']) or 'Lit_' in ' '.join(
                t['fix']) or 'Lit_' in ' '.join(t['buggy']):
            filtered_change_patterns.append(t)

    return filtered_change_patterns


def find_wrong_operand_in_binary_op_patterns(bug_seeding_patterns: List) -> List:
    filtered_patterns = []
    dup_filter = set()
    js_binary_operators = ["==", "!=", "===", "!==", "<", "<=", ">", ">=", "<<", ">>", ">>>", "\+", "-", "\*", "/", "%",
                           "\|",
                           "\^", "&", "in", "instanceof"]
    regexps = []
    for op in js_binary_operators:
        regexps.append(re.compile('(Idf_[\d]|Lit_[\d])\s(' + op + ')\s(Idf_[\d]|Lit_[\d])'))
    for pattern in bug_seeding_patterns:
        correct_part_of_pattern = ' '.join(pattern['fix'])
        buggy_part_of_pattern = ' '.join(pattern['buggy'])
        if pattern['fix_tokenType'] == 'BinaryExpression' and pattern['buggy_tokenType'] == 'BinaryExpression':
            for regex_op_1 in regexps:
                in_correct = regex_op_1.findall(correct_part_of_pattern)
                for regex_op_2 in regexps:
                    in_buggy = regex_op_2.findall(buggy_part_of_pattern)
                    for correct_match in in_correct:
                        for buggy_match in in_buggy:
                            if correct_match[1] == buggy_match[1] and correct_match[0] != buggy_match[0] and \
                                    correct_match[
                                        2] == buggy_match[2]:
                                pattern_as_str = correct_part_of_pattern + buggy_part_of_pattern
                                if pattern_as_str not in dup_filter:
                                    dup_filter.add(pattern_as_str)
                                    filtered_patterns.append(pattern)
                            if correct_match[1] == buggy_match[1] and correct_match[0] == buggy_match[0] and \
                                    correct_match[
                                        2] != buggy_match[2]:
                                pattern_as_str = correct_part_of_pattern + buggy_part_of_pattern
                                if pattern_as_str not in dup_filter:
                                    dup_filter.add(pattern_as_str)
                                    filtered_patterns.append(pattern)
    return filtered_patterns
