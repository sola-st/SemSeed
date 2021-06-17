"""

Created on 22-April-2020
@author Michael Pradel

Go through JSON files of a directory created by static analysis and map the positive and
negative examples.

"""

from typing import List, Dict, Union, Tuple
from pathlib import Path
import json
import codecs
from tqdm import tqdm
import pandas as pd


def read_file_content(file_path: Path) -> Union[List, Dict]:
    content = []
    try:
        with codecs.open(str(file_path), 'r', encoding='utf-8') as f:
            c = f.read()
            content = json.loads(c)
    except FileNotFoundError:
        pass
    except ValueError:
        pass
    return content


def read_create_dataset(in_dir: str) -> Dict:
    json_files = list(Path(in_dir).rglob(pattern='*.json'))

    bug_examples = {}
    # Each incorrect example will have a +ve (correct) and a possibly list of
    # -ve (incorrect) examples
    for file in tqdm(json_files, desc='Going through files'):
        extracted_data = read_file_content(file_path=file)
        tqdm.write(f"Current bug examples={len(bug_examples)}")
        for content in extracted_data:
            analysed_location = content['src']
            if '_SEMSEED_MUTATED_' in analysed_location:
                bug_seeding_metadata = read_file_content(analysed_location.split(' :')[0] + 'on')
                # analysed_location.split(' :')[0]
                # Get the original file name and the location where the bug was seeded. Create an unique key
                file_name = bug_seeding_metadata['file_name_where_intended']
                line = bug_seeding_metadata['target_line_range']['line'].split('-')
                line = ' - '.join(line)
                location_seeded_bug = file_name + ' : ' + line
                content['probability_that_incorrect'] = 1
                if location_seeded_bug not in bug_examples:
                    bug_examples[location_seeded_bug] = {
                        'correct': [],
                        'incorrect': []
                    }
                bug_examples[location_seeded_bug]['incorrect'].append(content)
            else:
                if analysed_location not in bug_examples:
                    bug_examples[analysed_location] = {
                        'correct': [],
                        'incorrect': []
                    }
                content['probability_that_incorrect'] = 0
                bug_examples[analysed_location]['correct'].append(content)
    return bug_examples


def process_bug_dataset(bug_dataset: Dict) -> List[List]:
    """
    There could be many examples where there is a positive example without a -ve
    example. Remove them and do other processing and return

    :param bug_dataset:
    :return:
    """
    filtered_data = []
    for file_path, data in tqdm(bug_dataset.items(), desc='Processing dataset'):
        if len(data['correct']) == 0 or len(data['incorrect']) == 0:
            continue
        # There could be multiple incorrect examples
        for ex in data['incorrect']:
            filtered_data.append([data['correct'][0], ex])
    return filtered_data


def filter_seeded_binOps(seeded_bugs: pd.DataFrame, seeded_bugs_binOps: pd.DataFrame):
    """
    Given the binOps from seeded bugs, extract only those locations
    where required
    """
    new_df = pd.DataFrame()
    i = 0
    for name, group in seeded_bugs_binOps.groupby('src', axis=0):
        i += 1
        if len(group) > 1:
            for _, row in group.iterrows():
                f = row['src'].split(':')[0].lstrip().rstrip()
                bugs_seeded_to_this_file = seeded_bugs.loc[seeded_bugs['file_name_where_intended'] == f]
                if len(bugs_seeded_to_this_file):
                    tok_seqs = bugs_seeded_to_this_file['target_token_sequence-Buggy']
                    for tk_seq in tok_seqs:
                        if len(tk_seq) > 3:
                            continue
                        s = [row['left'], row['op'], row['right']]
                        # print(s, tokens)
                        # if s == tokens:
                        #     print("Done")
                        #     new_df.append(row)
                print(f)
    print(len(new_df))


if __name__ == '__main__':
    """
    Before running me, first run extractFromJS once on the non seeded JS files and next on the bug-seeded
    JS files. This will create two separate JSON files in the 'benchmarks/binOps' directory.
    
    The current script will go through both JSON files and will map the correct code locations to 
    buggy code locations and finally write all together to dataset.json
    
    One may create another script to split dataset.json to training and validation data as two separate JSON
    files required for running DeepBugs.
        
    Eg. dataset.json
    [
        [
        {
          "left": "ID:g",
          "right": "LIT:67",
          "op": ">",
          "leftType": "unknown",
          "rightType": "number",
          "parent": "IfStatement",
          "grandParent": "BlockStatement",
          "src": "benchmarks/data/data/1.js : 6 - 6",
          "probability_that_incorrect": 0
        },
        {
          "left": "ID:g",
          "right": "LIT:67",
          "op": ">=",
          "leftType": "unknown",
          "rightType": "number",
          "parent": "IfStatement",
          "grandParent": "BlockStatement",
          "src": "benchmarks/js_benchmark_seeded_bugs/1_SEMSEED_MUTATED_1.js : 6 - 6",
          "probability_that_incorrect": 1
        }
        ]
    ]
    """
    # data_binOps = pd.read_pickle('benchmarks/binOps_data.pkl', 'gzip')[:100]

    seeded_bugs = pd.read_pickle('benchmarks/seeded_bugs_wrong_binary_operand.pkl', 'gzip')
    seeded_bugs_binOps = pd.read_pickle('benchmarks/binOps_wrong_operand_withloc.pkl', 'gzip')

    filter_seeded_binOps(seeded_bugs, seeded_bugs_binOps)
    # with open('benchmarks/dataset.json', 'w') as d:
    #     d.write(json.dumps(f))
