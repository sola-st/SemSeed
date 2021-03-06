'''
Created on Nov 9, 2017

@author: Michael Pradel
'''

import Util
from collections import Counter
import random
import pandas as pd

data = pd.read_pickle('benchmarks/binOps_data.pkl', 'gzip')
type_embedding_size = 5
node_type_embedding_size = 8  # if changing here, then also change in LearningDataBinOperator


class CodePiece(object):
    def __init__(self, left, right, op, src):
        self.left = left
        self.right = right
        self.op = op
        self.src = src

    def to_message(self):
        return str(self.src) + " | " + str(self.left) + " | " + str(self.op) + " | " + str(self.right)


class LearningData(object):
    def __init__(self):
        self.all_operators = None
        self.stats = {}

    def resetStats(self):
        self.stats = {}

    def pre_scan(self, training_data_paths, validation_data_paths):
        all_operators_set = set()
        for bin_op in Util.DataReader(training_data_paths):
            if isinstance(bin_op, list):
                for bop in bin_op:
                    all_operators_set.add(bop['op'])
            else:
                all_operators_set.add(bin_op["op"])
        for bin_op in Util.DataReader(validation_data_paths):
            if isinstance(bin_op, list):
                for bop in bin_op:
                    all_operators_set.add(bop['op'])
            else:
                all_operators_set.add(bin_op["op"])
        all_operators_set.update(set(data['op']))
        self.all_operators = list(all_operators_set)

    def code_to_xy_pairs_given_incorrect_example(self, bin_op, xs, ys, name_to_vector, type_to_vector,
                                                 node_type_to_vector, code_pieces):
        x_correct, y_correct = None, None
        x_incorrect, y_incorrect = None, None
        cor_incorrect_code_pieces = []
        for op in bin_op:
            left = op["left"]
            right = op["right"]
            operator = op["op"]
            left_type = op["leftType"]
            right_type = op["rightType"]
            parent = op["parent"]
            grand_parent = op["grandParent"]
            src = op["src"]
            if left not in name_to_vector:
                continue
            if right not in name_to_vector:
                continue
            left_vector = name_to_vector[left]
            right_vector = name_to_vector[right]
            operator_vector = [0] * len(self.all_operators)
            operator_vector[self.all_operators.index(operator)] = 1
            left_type_vector = type_to_vector.get(left_type, [0] * type_embedding_size)
            right_type_vector = type_to_vector.get(right_type, [0] * type_embedding_size)
            parent_vector = node_type_to_vector[parent]
            grand_parent_vector = node_type_to_vector[grand_parent]
            vec = left_vector + right_vector + operator_vector + left_type_vector + right_type_vector + parent_vector + grand_parent_vector
            if op['probability_that_incorrect'] == 0:
                x_correct = vec
                y_correct = [0]
            elif op['probability_that_incorrect'] == 1:
                x_incorrect = vec
                y_incorrect = [1]
            cor_incorrect_code_pieces.append(CodePiece(left, right, operator, src))

        if x_correct and y_correct and x_incorrect and y_incorrect:
            xs.append(x_correct)
            ys.append(y_correct)
            xs.append(x_incorrect)
            ys.append(y_incorrect)
            code_pieces.extend(cor_incorrect_code_pieces)

    def code_to_xy_pairs(self, bin_op, xs, ys, name_to_vector, type_to_vector, node_type_to_vector, code_pieces):
        left = bin_op["left"]
        right = bin_op["right"]
        operator = bin_op["op"]
        left_type = bin_op["leftType"]
        right_type = bin_op["rightType"]
        parent = bin_op["parent"]
        grand_parent = bin_op["grandParent"]
        src = bin_op["src"]
        if not (left in name_to_vector):
            return
        if not (right in name_to_vector):
            return

        left_vector = name_to_vector[left]
        right_vector = name_to_vector[right]
        operator_vector = [0] * len(self.all_operators)
        operator_vector[self.all_operators.index(operator)] = 1
        left_type_vector = type_to_vector.get(left_type, [0] * type_embedding_size)
        right_type_vector = type_to_vector.get(right_type, [0] * type_embedding_size)
        parent_vector = node_type_to_vector[parent]
        grand_parent_vector = node_type_to_vector[grand_parent]

        # for all xy-pairs: y value = probability that incorrect
        x_correct = left_vector + right_vector + operator_vector + left_type_vector + right_type_vector + parent_vector + grand_parent_vector
        y_correct = [0]
        xs.append(x_correct)
        ys.append(y_correct)
        code_pieces.append(CodePiece(left, right, operator, src))

        # pick some other, likely incorrect operator
        other_operator_vector = None
        while other_operator_vector == None:
            other_operator = random.choice(self.all_operators)
            if other_operator != operator:
                other_operator_vector = [0] * len(self.all_operators)
                other_operator_vector[self.all_operators.index(other_operator)] = 1

        x_incorrect = left_vector + right_vector + other_operator_vector + left_type_vector + right_type_vector + parent_vector + grand_parent_vector
        y_incorrect = [1]
        xs.append(x_incorrect)
        ys.append(y_incorrect)
        code_pieces.append(CodePiece(left, right, other_operator, src))

    def anomaly_score(self, y_prediction_orig, y_prediction_changed):
        return y_prediction_orig

    def normal_score(self, y_prediction_orig, y_prediction_changed):
        return y_prediction_changed
