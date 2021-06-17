"""

Created on 24-March-2020
@author Jibesh Patra

"""

from typing import List, Dict

import numpy as np

from bug_seeding_approaches.SeedBugs import SeedBugs
from bug_seeding_approaches.SemSeed.BugSeedingUtils import get_cosine_distance_between_tokens, \
    perform_analogy_queries_to_get_unbound_token, get_identifiers_given_scope_of_selection, \
    get_literals_given_scope_of_selection


class SemSeedBugs(SeedBugs):

    def __init__(self, bug_seeding_pattern: Dict, target_location: Dict, file_path: str,
                 available_identifiers: Dict, available_literals: Dict,
                 similarity_threshold: float = 0.2, K: int = 1, scope_of_selection='function'):
        """
        Seed a bug using SemSeed
        :param similarity_threshold: The similarity threshold that will be used to check if bug may be seeded Ranges
                                     between 0.0 - 1.0 (1.0 means only seed if exactly similar)
        :param K: If K=1, use the best unbound token to seed the bug. If K=10, choose the top 10
        """
        super().__init__(bug_seeding_pattern=bug_seeding_pattern, target_location=target_location, file_path=file_path)
        self.similarity_threshold = similarity_threshold
        self.identifiers_available_for_selecting_unbound_token = get_identifiers_given_scope_of_selection(
            available_idfs_in_scopes=available_identifiers,
            scope_of_selection=scope_of_selection,
            target_function_range=target_location['belonging_function_range']
        )
        self.literals_available_for_selecting_unbound_token = get_literals_given_scope_of_selection(
            available_lits_in_scopes=available_literals,
            scope_of_selection=scope_of_selection,
            target_function_range=target_location['belonging_function_range']
        )
        self.K = K
        self.SPECIAL_TOKEN = '__UNBOUND__TOKEN__'

    def is_matching_token_sequence(self) -> bool:
        target = self.target_location
        seeding_pattern = self.bug_seeding_pattern

        # Pure syntactic match only compares the abstracted tokens
        if target['abstractedTokens'] != seeding_pattern['fix']:
            return False

        seeding_pattern_correct_tok_seq = seeding_pattern['fix_actual']
        target_token_sequence = target['tokens']

        cosine_similarities = []
        for i, abs_tok in enumerate(target['abstractedTokens']):
            # Do not care about tokens that are not Identifiers or Literals
            if not abs_tok.startswith('Idf_') and not abs_tok.startswith('Lit_'):
                continue

            # Find cosine similarity
            if seeding_pattern_correct_tok_seq[i] == target_token_sequence[i]:
                # If the tokens are exactly same, no point in doing anything else
                similarity = 1.0
            else:
                similarity = round(1 - get_cosine_distance_between_tokens(
                    label1=seeding_pattern_correct_tok_seq[i], label2=target_token_sequence[i]), 3)
            cosine_similarities.append(similarity)

        cosine_similarities = np.array(cosine_similarities)

        mean_similarity = np.mean(cosine_similarities)

        self.bug_metadata['mean_similarity'] = mean_similarity
        # If the average cosine_similarities are greater equal to threshold
        if mean_similarity >= self.similarity_threshold:
            return True
        else:
            return False

    def apply_pattern(self) -> List[List]:
        # The mutated token sequences we are generating
        mutated_token_sequences = []

        # Create a mapping between abstract token to concrete
        idf_lit_mapping_of_target = self.get_abstract_token_to_concrete_mapping()

        # All Identifiers and Literals present in the target
        idfs_lits_in_target, identifiers_in_target, literals_in_target = self.extract_tokens_of_kinds(
            given_token_seq=self.target_location['tokens'])
        # All Identifiers and Literals present in the 'correct' part of the pattern
        idfs_lits_in_pattern, identifiers_in_pattern, literals_in_pattern = self.extract_tokens_of_kinds(
            given_token_seq=self.bug_seeding_pattern['fix_actual'])

        # Filter Identifiers and Literals already present in the target from the scope of selection
        available_identifiers_for_unbound_token = list(self.identifiers_available_for_selecting_unbound_token - set(
            identifiers_in_target))
        available_literals_for_unbound_token = list(self.literals_available_for_selecting_unbound_token - set(
            literals_in_target))

        mutated_token_sequence = []
        idx_to_unbound_tokens = {}
        # Go over the abstract tokens of the 'buggy' part of the bug seeding pattern
        for i, abstract_token_in_seeding_pattern in enumerate(self.bug_seeding_pattern['buggy']):

            # *** If not Identifier/Literal, simply copy the token and go to the next token ***
            if not abstract_token_in_seeding_pattern.startswith(
                    'Idf_') and not abstract_token_in_seeding_pattern.startswith('Lit_'):
                mutated_token_sequence.append(abstract_token_in_seeding_pattern)
                continue

            # *** If the abstracted token is of type Identifier/Literal ***

            # If the abstract token matches that of target then simply use that Identifier/Literal
            if abstract_token_in_seeding_pattern in idf_lit_mapping_of_target:
                mutated_token_sequence.append(
                    idf_lit_mapping_of_target[abstract_token_in_seeding_pattern])
            else:  # The seeding needs an unbound token
                # The selected_unbound_token whose analogous token has to be found
                unbound_token_in_pattern = self.bug_seeding_pattern['buggy_actual'][i]

                if abstract_token_in_seeding_pattern.startswith('Idf_'):
                    candidates = available_identifiers_for_unbound_token
                else:
                    candidates = available_literals_for_unbound_token

                selected_unbound_tokens = perform_analogy_queries_to_get_unbound_token(
                    tokens_in_pattern=idfs_lits_in_pattern,
                    unbound_token_in_pattern=unbound_token_in_pattern,
                    tokens_in_target=idfs_lits_in_target,
                    candidate_tokens=candidates,
                    best_k_matching_unbound_token=self.K,
                )
                # We do not immediately append it, rather collect all possible and append later
                idx_to_unbound_tokens[i] = selected_unbound_tokens
                mutated_token_sequence.append('__PLACEHOLDER__')

        # Calculate the number of possible variants
        possible_variants = 1
        for idx, selected_unbound_tokens in idx_to_unbound_tokens.items():
            possible_variants *= len(selected_unbound_tokens)

        mutated_token_sequences = [mutated_token_sequence] * possible_variants
        # Seeding bug did not need any unbound token
        if len(idx_to_unbound_tokens) == 0:
            return mutated_token_sequences
        else:
            for idx, selected_unbound_tokens in idx_to_unbound_tokens.items():
                j = 0
                # If for some index, an unbound token could not be selected then it is not possible to seed a bug
                if len(selected_unbound_tokens) == 0:
                    mutated_token_sequences = []
                    return mutated_token_sequences
                else:
                    possible_variants /= len(selected_unbound_tokens)
                    while j < len(mutated_token_sequences):
                        s = 0
                        while s < len(selected_unbound_tokens):
                            t = list(mutated_token_sequences[j])
                            t[idx] = selected_unbound_tokens[s]
                            if (j + 1) % possible_variants == 0:
                                s += 1
                            mutated_token_sequences[j] = t
                            j += 1
                            # mutated_token_sequences.append(t)
            return mutated_token_sequences
