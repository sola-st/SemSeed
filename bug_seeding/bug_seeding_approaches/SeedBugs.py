"""

Created on 24-March-2020
@author Jibesh Patra

"""
from abc import ABC, abstractmethod
from typing import List, Tuple


class SeedBugs(ABC):
    def __init__(self, bug_seeding_pattern: dict, target_location: dict, file_path: str):
        # Stuffs about the bug. Eg. Buggy, Correct, Surrounding tokens, Usages Identifiers, Literals etc.

        self.bug_metadata = {
            'file_name_where_intended': file_path,
            "target_token_sequence-Correct": target_location['tokens'],  # Abstract token sequence that will be mutated
            "target_token_sequence-Buggy": [],  # Concrete token sequence generated after mutation
            "token_sequence_abstraction-Correct": target_location['abstractedTokens'],
            "token_sequence_abstraction-Buggy": [],
            "target_line_range": {'line': target_location['line'], 'range': target_location['range']},
            "num_of_available_identifiers_to_choose_from": 0,
            "num_of_available_literals_to_choose_from": 0,
            "error": False
        }
        self.bug_seeding_pattern = bug_seeding_pattern
        self.target_location = target_location

    @abstractmethod
    def is_matching_token_sequence(self) -> bool:
        """
        For a 'syntactic' match check, this will return True if the
        token sequence in abstracted form match.

        For a 'semantic' matching this will depend on the cosine distance of the
        embedding of the tokens along with the threshold.
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def apply_pattern(self) -> List[List]:
        """
        Seed a bug by applying a given pattern
        :return:
        """
        raise NotImplementedError

    def extract_tokens_of_kinds(self, given_token_seq: List[str]) -> Tuple[List, List, List]:
        try:
            assert len(given_token_seq) == len(self.target_location['abstractedTokens'])
        except AssertionError as e:
            print("The lengths of these token sequences should be same")

        tokens = []
        idf_tokens = []
        lit_tokens = []

        idf_prefix = 'Idf_'
        lit_prefix = 'Lit_'

        for i, abs_tok in enumerate(self.target_location['abstractedTokens']):
            concrete_token = given_token_seq[i]
            if abs_tok.startswith(idf_prefix) or abs_tok.startswith(lit_prefix):
                tokens.append(concrete_token)
            if abs_tok.startswith(idf_prefix):
                idf_tokens.append(concrete_token)
            elif abs_tok.startswith(lit_prefix):
                lit_tokens.append(concrete_token)
        return tokens, idf_tokens, lit_tokens

    def replace_target_with_mutated_token_sequence(self, token_list: List, token_range_list: List,
                                                   mutated_token_sequence: List) -> List:
        """
        Once the mutated token sequence has been found replace the target token sequence with this new
        :param token_list: The complete list of the token in the file
        :param token_range_list: The ranges of each token contained in the token list
        :param mutated_token_sequence: The token sequence that will be inserted to seed bugs
        :return: Token sequence after seeding the bug
        """

        assert len(token_list) == len(token_range_list)

        start_range = self.target_location["range"][0]
        end_range = self.target_location["range"][1]

        indices_to_remove = [i for i, rng in enumerate(token_range_list) if int(rng.split(
            '-')[0]) >= start_range and int(rng.split('-')[1]) <= end_range]

        part1 = token_list[:indices_to_remove[0]]
        part2 = token_list[indices_to_remove[-1] + 1:]

        token_list_after_seeding = part1 + mutated_token_sequence + part2
        assert len(token_list_after_seeding) == len(token_list) - len(self.target_location['tokens']) + len(
            mutated_token_sequence)
        return token_list_after_seeding

    def get_abstract_token_to_concrete_mapping(self) -> dict:
        """
        This creates a mapping of the abstract token to its actual value
        Eg. 'Idf_1' -> 'a'
        """
        mappings = {}
        for i, abstract_tok in enumerate(self.target_location['abstractedTokens']):
            if not abstract_tok.startswith('Idf_') and not abstract_tok.startswith('Lit_'):
                continue
            mappings[abstract_tok] = self.target_location['tokens'][i]
        return mappings

    def write_bug_seeded_file(self):
        pass

    def __call__(self, *args, **kwargs):
        pass
