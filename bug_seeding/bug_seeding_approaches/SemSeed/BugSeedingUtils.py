import os
from threading import Timer
import numpy as np
import subprocess
from scipy.spatial.distance import cosine as cosine_distance
import scipy
from typing import List
import fasttext

token_embedding = fasttext.load_model(path='benchmarks/all_token_embedding_FAST_TEXT.bin')


def get_cosine_distance_between_tokens(label1, label2):
    v1 = token_embedding[label1]
    v2 = token_embedding[label2]
    return round(scipy.spatial.distance.cosine(v1, v2), 3)


def perform_analogy_queries_to_get_unbound_token(tokens_in_pattern: List, unbound_token_in_pattern: str,
                                                 tokens_in_target: List,
                                                 candidate_tokens: List,
                                                 best_k_matching_unbound_token: int
                                                 ) -> List[str]:
    """
    - Find the difference between all tokens in tokens_in_pattern with unbound_token_in_pattern
    - Pick a token from candidate_tokens that closely 'matches' this difference with existing_labels_in_target

    Eg.

     a = b + c + 1 (correct) => a = b + c + 1 + m  (buggy)

     x = y + z + 2 (target)  => x = y + z + 2 + ?  (seeded bug)

    tokens_in_pattern --> [a, b, c, 1] known from the correct
    unbound_token_in_pattern --> m
    tokens_in_target --> [x, y, z, 2]
    candidate_tokens --> tokens in some given scope (e.g., same function, same file) where 'x = y + z + 2' exists.
    We want to select a token from candidate_tokens and the query looks something like the following.

    The way:
        (a, b, c, 1) is related to 'm'
        (x, y, z, 2) is related to '?' from candidate_tokens

    :param tokens_in_pattern: Tokens in the 'correct' part of the pattern that we imitate
    :param unbound_token_in_pattern: The token for which we want an analogous token
    :param tokens_in_target: Token sequence where we want to seed bug
    :param candidate_tokens: We select one token from the candidate tokens using analogy queries
    :param best_k_matching_unbound_token:
    :return:
    """
    try:
        assert len(tokens_in_pattern) == len(tokens_in_target)
    except AssertionError:
        print("The length of source and target tokens must be same")

    try:
        assert len(candidate_tokens) > 0
    except AssertionError:
        print("There must be at least one token to select from ")

    ref_label_vec = token_embedding[unbound_token_in_pattern]
    analogous_token_embeddings = []

    for i, src_label in enumerate(tokens_in_pattern):
        analogous_token_embeddings.append(ref_label_vec -
                                          token_embedding[src_label] + token_embedding[tokens_in_target[i]])

    if len(analogous_token_embeddings) > 0:
        sum_analogous_vectors = np.sum(analogous_token_embeddings, axis=0)
    else:
        sum_analogous_vectors = 0

    candidate_token_embeddings = [token_embedding[label] for label in candidate_tokens]

    selected_tokens = []
    avg_analogous_embedding = sum_analogous_vectors / len(analogous_token_embeddings)

    if isinstance(sum_analogous_vectors, np.ndarray):
        # Now we need to find the 'token' from 'candidate_tokens' that is most similar to the sum of analogous
        # embeddings
        similarities = [1 - cosine_distance(avg_analogous_embedding, candidate_token_embedding)
                        for candidate_token_embedding in candidate_token_embeddings]
        most_similar_indices = np.argsort(similarities)[::-1][:best_k_matching_unbound_token]
        selected_tokens = [candidate_tokens[i] for i in most_similar_indices]
        # selected_token = candidate_tokens[int(np.argmax(similarities))]
    else:  # For cases where there does not exist any label that may be compared to find an analogous label Eg.
        # return a;
        selected_tokens.append(get_closest_matching_label(unbound_token_in_pattern, candidate_tokens))
    return selected_tokens


def get_closest_matching_label(unbound_token_in_pattern: str, candidate_tokens: List) -> str:
    """
    Given a unbound_token_in_pattern and a list of candidate_tokens, find the closest
    matching token and return it
    :param unbound_token_in_pattern:
    :param candidate_tokens:
    :return:
    """
    distances = []
    for cur_label in candidate_tokens:
        distance = get_cosine_distance_between_tokens(
            label1=unbound_token_in_pattern, label2=cur_label)
        distances.append(distance)
    min_idx = int(np.argmin(distances))
    return candidate_tokens[min_idx]


def remove_subsumed_nodes(all_mutable_nodes):
    """
    We do not want to mutate the same locations multiple times. Eg.
    For code --> a && b ( m && n )
    There could be the following patterns that may be applied here:
        * Idf_1 && Idf_2 (Idf_3 && Idf4) --> Idf_1 || Idf_2 (Idf_3 || Idf4)
        * Idf_1 && Idf_2 --> Idf_1 || Idf_3
    Now the question is, which one of these patterns should we choose to apply?

    We do very similar to what we did while extracting patterns i.e., Select the patterns that has
    maximum tokens.
    """
    node_indices_to_remove = []

    for i, node1 in enumerate(all_mutable_nodes):
        node1_rng_start, node1_rng_end = node1['range'][0], node1['range'][1]
        for j, node2 in enumerate(all_mutable_nodes):
            node2_rng_start, node2_rng_end = node2['range'][0], node2['range'][1]

            # If the exact same node, continue to the next
            if node1_rng_start == node2_rng_start and node1_rng_end == node2_rng_end:
                continue

            if node2_rng_start >= node1_rng_start and node2_rng_end <= node1_rng_end:
                # Means node1 subsumes node2. So remove node2
                node_indices_to_remove.append(j)

    # Actually remove the node.
    for idx in node_indices_to_remove:
        del all_mutable_nodes[idx]


def _callNodeJS_ApplyMutations(arguments):
    mutated_nodes_file_path, js_file_where_to_apply_mutations, bug_seeded_js_out_dir = arguments

    path_to_process = os.path.join(os.path.normpath(
        os.getcwd() + os.sep), 'SemSeed', 'extract_abstracted_code_changes', 'applyMutations.js')

    time_out_before_killing = 180  # seconds
    try:
        def kill_process(p):
            return p.kill()

        p = subprocess.Popen([
            'node', path_to_process,
            '-inFile_MutatedNodes', mutated_nodes_file_path,
            '-inFile_JSFilePath', js_file_where_to_apply_mutations,
            '-outDir', bug_seeded_js_out_dir,
        ],
            stdout=subprocess.PIPE)
        time_out = Timer(time_out_before_killing, kill_process, [p])
        try:
            time_out.start()
            stdout, stderr = p.communicate()
            # print(stdout)
        finally:
            time_out.cancel()
    except subprocess.TimeoutExpired:
        # p.kill()
        pass


def get_identifiers_given_scope_of_selection(available_idfs_in_scopes: dict, scope_of_selection: str,
                                             target_function_range: str) -> set:
    """
    Given identifiers in different scopes and the scope of selection,
    get the list of possible Identifiers that may be used as an unbound Identifier token
    :param available_idfs_in_scopes:
    :param scope_of_selection:
    :param target_function_range: The range (token location) of the function where the target is present
    :return:
    """
    if scope_of_selection == 'function':
        return set(available_idfs_in_scopes['functions_to_identifiers'][target_function_range])
    elif scope_of_selection == 'file':
        return set(available_idfs_in_scopes['all_identifiers_in_same_file'])
    else:  # Also include top-K most frequent
        return set(available_idfs_in_scopes['all_identifiers_in_same_file'] + available_idfs_in_scopes[
            'K_most_frequent_identifiers'])


def get_literals_given_scope_of_selection(available_lits_in_scopes: dict, scope_of_selection: str,
                                          target_function_range: str) -> set:
    """
    Given literals in different scopes and the scope of selection,
    get the list of possible literals that may be used as an unbound literal token
    :param available_lits_in_scopes:
    :param scope_of_selection:
    :param target_function_range: The range (token location) of the function where the target is present
    :return:
    """
    if scope_of_selection == 'function':
        return set(available_lits_in_scopes['functions_to_literals'][target_function_range])
    elif scope_of_selection == 'file':
        return set(available_lits_in_scopes['all_literals_in_same_file'])
    else:  # Also include top-K most frequent
        return set(available_lits_in_scopes['all_literals_in_same_file'] + available_lits_in_scopes[
            'K_most_frequent_literals'])
