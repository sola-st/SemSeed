"""

Created on 25-March-2020
@author Jibesh Patra

This file contains helper functions to parse the static analysis results
extracted using nodejs and esprima
"""
from typing import List, Dict


def get_all_tokens_in_file(range_to_token_mapping: Dict) -> List:
    tokens = set()
    for token in range_to_token_mapping.values():
        tokens.add(token)
    return list(tokens)


def get_tokens_from_different_scopes(analysed_file: dict, kind: str, k_most_frequent: List) -> Dict:
    if kind == 'identifier':
        return {
            'all_identifiers_in_same_file': get_all_tokens_in_file(
                analysed_file['range_to_identifier']),
            # A mapping between the functions in the file and the containing Identifiers
            'functions_to_identifiers': analysed_file['functions_to_identifiers'],
            'K_most_frequent_identifiers': k_most_frequent  # 1000 most frequent Identifiers
        }
    else:
        return {
            'all_literals_in_same_file': get_all_tokens_in_file(
                analysed_file['range_to_literal']),
            # A mapping between the functions in the file and the containing Literals
            'functions_to_literals': analysed_file['functions_to_literals'],
            'K_most_frequent_literals': k_most_frequent  # 1000 most frequent Literals
        }
