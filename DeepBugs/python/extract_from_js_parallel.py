"""

Created on 09-July-2020
@author Michael Pradel

Call

'node extractFromJS --file data/one.js'
"""
import os
import subprocess
from threading import Timer
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from typing import List
import random
import codecs
import json
from pathlib import Path
from collections import defaultdict

random.seed(a=42)


def extractFromJS(target_js_file_path: str, line_num: int) -> str:
    """
    Prepare a JS file for seeding bugs by converting JS file to AST nodes.
    The functions creates a Nodejs process to extract the required data.
    :param target_js_file_path: The input JS file that will be converted to AST node representations
    :param out_json_file_path:
    :return:
    """

    def kill_process(p):
        return p.kill()

    err_in_execution = False
    path_to_process = os.path.join(os.path.normpath(
        os.getcwd() + os.sep), 'javascript', 'extractFromJS.js')
    time_out_before_killing = 240  # seconds
    try:
        p = subprocess.Popen([
            'node', path_to_process,
            what,
            '--file', target_js_file_path,
            line_num
        ],
            stdout=subprocess.PIPE)
        time_out = Timer(time_out_before_killing, kill_process, [p])
        try:
            time_out.start()
            stdout, stderr = p.communicate()
            tqdm.write(stdout.decode("utf-8"))
            if stderr:
                err_in_execution = stderr.decode("utf-8")
                # tqdm.write(err_in_execution)
        finally:
            time_out.cancel()
    except subprocess.TimeoutExpired:
        pass
    return err_in_execution


def remove_duplicates(file_list: List, duplicate_file_groups: List) -> List:
    """
    Given a list of files, and known duplicates, keep only one of the duplicates
    :param duplicate_file_groups:
    :param file_list:
    :return:
    """
    dup_files = set()
    for file_group in duplicate_file_groups:
        # Except the first file rest are all duplicates
        dup_files.update(file_group[1:])

    files_without_duplicates = []
    # Now, we remove the known duplicates
    root_dir = '/data/'
    # dup_files = set([os.path.join(root_dir, fp) for fp in dup_files])
    for fl_path in file_list:
        if fl_path.split(root_dir)[1] not in dup_files:
            files_without_duplicates.append(fl_path)
    return files_without_duplicates


def read_json_file(json_file_path):
    try:
        obj_text = codecs.open(json_file_path, 'r', encoding='utf-8').read()
        return json.loads(obj_text)
    except FileNotFoundError:
        print(f"*** Can't find {json_file_path} provide a correct path")
        return {}
    except Exception as e:
        # Empty JSON file most likely due to abrupt killing of the process while writing
        # print (e)
        return {}


def add_required_line_number(file_path):
    """
    Add the required line number where bug was seeded
    :return:
    """
    file_path = str(file_path)
    seeded_bug_info = read_json_file(file_path + 'on')
    line = seeded_bug_info["target_line_range"]["line"]
    return file_path, line


def extractFromJS_multi(arg):
    if isinstance(arg, tuple):
        file, loc = arg
    else:
        file = arg
        loc = "null"

    extractFromJS(target_js_file_path=file, line_num=loc)


def semseed_seeded_extraction(in_dir, what):
    print(f"Reading files from {in_dir}")
    js_files = list(Path(in_dir).rglob('*.js'))
    js_files = [f for f in js_files if Path(f).is_file()]
    if in_dir.endswith('/data'):
        js_files = [str(f) for f in js_files]
        print(" Removing duplicates from {} files in benchmarks".format(len(js_files)))
        duplicate_file_groups = read_json_file('benchmarks/js150-duplicates.json')
        js_files = remove_duplicates(file_list=js_files, duplicate_file_groups=duplicate_file_groups)
    else:
        print("Adding line numbers to extract")
        line_out_file = f'benchmarks/files_and_line_numbers_wrong_{what}.json'
        if Path(line_out_file).is_file():
            print("Reading from pre-computed")
            with open(line_out_file, 'r') as f:
                js_file_with_lines = json.load(f)
            js_files = [(f, line[0]) for f, line in
                        js_file_with_lines.items()]  # every file is unique and has only one line
        else:
            js_file_with_lines = defaultdict(list)
            with Pool(cpu_count() // 2) as p:
                with tqdm(total=len(js_files)) as pbar:
                    pbar.set_description_str(desc="Adding line numbers", refresh=False)
                    for _, files_and_lines in enumerate(p.imap_unordered(add_required_line_number, js_files, 10)):
                        js_file_with_lines[files_and_lines[0]].append(files_and_lines[1])
                        # print(files_and_lines)
                        pbar.update()
                    p.close()
                    p.join()
            with open(line_out_file, 'w+') as o:
                json.dump(js_file_with_lines, o)
            js_files = [(f, line[0]) for f, line in
                        js_file_with_lines.items()]
            # js_files = [(f,l) for f, l in js_files if 'elastic_SEMSEED' in f]
    # random.shuffle(js_files)
    # js_files = js_files[:10]
    with Pool(processes=cpu_count()) as p:
        with tqdm(total=len(js_files)) as pbar:
            pbar.set_description_str(
                desc="Extract from JS", refresh=False)
            for i, execution_errors in tqdm(
                    enumerate(p.imap_unordered(extractFromJS_multi,
                                               js_files, chunksize=10))):
                # ex_errors.append(execution_errors)
                pbar.update()
            p.close()
            p.join()
    # print(ex_errors)


def real_bugs_GitHub_extraction(in_dir):
    js_files = list(Path(in_dir).rglob('*.js'))
    js_files = [str(f) for f in js_files if Path(f).is_file()]

    js_files_with_lines = []
    for file_path in tqdm(js_files, desc='Adding lines'):
        file_name = os.path.basename(file_path)
        line = file_name.split('_')[2]
        js_files_with_lines.append((file_path, f'{line}-{line}'))
    with Pool(processes=cpu_count()) as p:
        with tqdm(total=len(js_files)) as pbar:
            pbar.set_description_str(
                desc="Extract from JS", refresh=False)
            for i, execution_errors in tqdm(
                    enumerate(p.imap_unordered(extractFromJS_multi,
                                               js_files_with_lines, chunksize=10))):
                # print(execution_errors)
                # ex_errors.append(execution_errors)
                pbar.update()
            p.close()
            p.join()


if __name__ == '__main__':
    what = ['binOps', 'assignments'][1]
    in_dir = \
        ['benchmarks/js_benchmark_seeded_bugs_wrong_assignment',
         'benchmarks/js_benchmark_seeded_bugs_wrong_binop_operand',
         'benchmarks/real_bugs_github',
         'benchmarks/data'][2]
    # semseed_seeded_extraction(in_dir, what)
    real_bugs_GitHub_extraction(in_dir)
