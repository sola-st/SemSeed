'''
Created on Nov 13, 2017

@author: Michael Pradel
'''

import Util
from collections import namedtuple
import random

type_embedding_size = 5
node_type_embedding_size = 8  # if changing here, then also change in LearningDataBinOperator
import pandas as pd
from tqdm import tqdm
import json
# from pathlib import Path
# data = pd.read_pickle('benchmarks/binOps_data.pkl','gzip')
# data['src_no_loc'] = data['src'].apply(lambda x: x.split(':')[0].lstrip().rstrip())
class CodePiece(object):
    def __init__(self, left, right, op, src):
        self.left = left
        self.right = right
        self.op = op
        self.src = src

    def to_message(self):
        return str(self.src) + " | " + str(self.left) + " | " + str(self.op) + " | " + str(self.right)


Operand = namedtuple('Operand', ['op', 'type'])


class LearningData(object):
    def __init__(self):
        self.file_to_operands = dict()  # string to set of Operands
        self.stats = {}

    def resetStats(self):
        self.stats = {}

    def pre_scan(self, training_data_paths, validation_data_paths):
        all_operators_set = set()
        all_binops = list(Util.DataReader(training_data_paths))
        # all_binops=all_binops[:100]
        # preprocessed_json_file_path = 'benchmarks/file_to_operands_wrongbinOpnd.json'
        # preprocessed = None
        # if Path(preprocessed_json_file_path).is_file():
        #     print(f'Reading {preprocessed_json_file_path}')
        #     with open(preprocessed_json_file_path, 'r') as f:
        #         preprocessed = json.load(f)
        for bin_op in tqdm(all_binops, desc='Preprocessing'):
            if isinstance(bin_op, list):
                for bop in bin_op:
                    file = bop["src"].split(" : ")[0]
                    operands = self.file_to_operands.setdefault(file, set())
                    left_operand = Operand(bop["left"], bop["leftType"])
                    right_operand = Operand(bop["right"], bop["rightType"])
                    operands.add(left_operand)
                    operands.add(right_operand)
                    all_operators_set.add(bop["op"])
            else:
                file = bin_op["src"].split(" : ")[0]
                if file in self.file_to_operands:
                    continue
                operands = self.file_to_operands.setdefault(file, set())
                left_operand = Operand(bin_op["left"], bin_op["leftType"])
                right_operand = Operand(bin_op["right"], bin_op["rightType"])
                operands.add(left_operand)
                operands.add(right_operand)

                all_operators_set.add(bin_op["op"])
                # if preprocessed and file in preprocessed:
                #     operands_in_file = preprocessed[file]
                #     for opnd, tp in zip(operands_in_file['operand'], operands_in_file['type']):
                #         operands.add(Operand(opnd, tp))
                # else:
                #     all_binops_current_file: pd.DataFrame = data[data['src_no_loc'] == file.lstrip().rstrip()]
                #     # print(len(all_binops_current_file))
                #     if len(all_binops_current_file):
                #         for _, row in all_binops_current_file.iterrows():
                #             bop = row.to_dict()
                #             left_operand = Operand(bop["left"], bop["leftType"])
                #             right_operand = Operand(bop["right"], bop["rightType"])
                #             operands.add(left_operand)
                #             operands.add(right_operand)
                #             all_operators_set.add(bop["op"])
        for bin_op in Util.DataReader(validation_data_paths):
            if isinstance(bin_op, list):
                for bop in bin_op:
                    file = bop["src"].split(" : ")[0]
                    operands = self.file_to_operands.setdefault(file, set())
                    left_operand = Operand(bop["left"], bop["leftType"])
                    right_operand = Operand(bop["right"], bop["rightType"])
                    operands.add(left_operand)
                    operands.add(right_operand)
                    all_operators_set.add(bop["op"])
            else:
                file = bin_op["src"].split(" : ")[0]
                operands = self.file_to_operands.setdefault(file, set())
                left_operand = Operand(bin_op["left"], bin_op["leftType"])
                right_operand = Operand(bin_op["right"], bin_op["rightType"])
                operands.add(left_operand)
                operands.add(right_operand)

                all_operators_set.add(bin_op["op"])
        # if not Path(preprocessed_json_file_path).is_file():
        #     print("Prescan done, now saving the pre scan results")
        #     file_to_opnd={}
        #     for file, operands in self.file_to_operands.items():
        #         if file not in file_to_opnd:
        #             file_to_opnd[file] = {
        #             'operand':[],
        #             'type':[]
        #             }
        #         for op in operands:
        #             file_to_opnd[file]['operand'].append(op[0])
        #             file_to_opnd[file]['type'].append(op[1])
        #     with open(preprocessed_json_file_path,'w+') as f:
        #         json.dump(file_to_opnd, f)
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
                return
            if right not in name_to_vector:
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
            vec = left_vector + right_vector + operator_vector + left_type_vector + right_type_vector + parent_vector + grand_parent_vector

            if int(op['probability_that_incorrect']) == 0:
                x_correct = vec
                y_correct = [0]
            elif int(op['probability_that_incorrect']) == 1:
                x_incorrect = vec
                y_incorrect = [1]
            cor_incorrect_code_pieces.append(CodePiece(left, right, operator, src))
        if x_correct and y_correct and x_incorrect and y_incorrect:
            xs.append(x_correct)
            ys.append(y_correct)

            xs.append(x_incorrect)
            ys.append(y_incorrect)
            code_pieces.append(cor_incorrect_code_pieces)

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

        # find an alternative operand in the same file
        replace_left = random.random() < 0.5
        if replace_left:
            to_replace_operand = left
        else:
            to_replace_operand = right
        file = src.split(" : ")[0]
        all_operands = self.file_to_operands[file]
        tries_left = 100
        found = False
        while (not found) and tries_left > 0:
            other_operand = random.choice(list(all_operands))
            if other_operand.op in name_to_vector and other_operand.op != to_replace_operand:
                found = True
            tries_left -= 1

        if not found:
            return

        # for all xy-pairs: y value = probability that incorrect
        x_correct = left_vector + right_vector + operator_vector + left_type_vector + right_type_vector + parent_vector + grand_parent_vector
        y_correct = [0]
        xs.append(x_correct)
        ys.append(y_correct)
        code_pieces.append(CodePiece(left, right, operator, src))

        other_operand_vector = name_to_vector[other_operand.op]
        other_operand_type_vector = type_to_vector[other_operand.type]
        # replace one operand with the alternative one
        if replace_left:
            x_incorrect = other_operand_vector + right_vector + operator_vector + other_operand_type_vector + right_type_vector + parent_vector + grand_parent_vector
        else:
            x_incorrect = left_vector + other_operand_vector + operator_vector + right_type_vector + other_operand_type_vector + parent_vector + grand_parent_vector
        y_incorrect = [1]
        xs.append(x_incorrect)
        ys.append(y_incorrect)
        code_pieces.append(CodePiece(right, left, operator, src))

    def anomaly_score(self, y_prediction_orig, y_prediction_changed):
        return y_prediction_orig

    def normal_score(self, y_prediction_orig, y_prediction_changed):
        return y_prediction_changed
