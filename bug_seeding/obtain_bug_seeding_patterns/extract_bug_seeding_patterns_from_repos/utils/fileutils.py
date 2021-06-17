"""
Created on 10-March-2020
@author Jibesh Patra

This script contains some utility functions for filesystem operations
"""
import json
from pathlib import Path
import os
from typing import List, Any, Union, Dict
import codecs
import shutil
import random
import gzip
from zipfile import ZipFile, BadZipFile
from tarfile import TarFile, ExtractError
from tqdm import tqdm

random.seed(42)


def read_json_file(json_file_path: str) -> Union[List, Dict]:
    """ Read a JSON file given the p """
    if Path(json_file_path).suffix == '.gz':
        try:
            with gzip.GzipFile(json_file_path, 'r') as fin:
                return json.loads(fin.read().decode('utf-8'))
        except FileNotFoundError:
            print(f"*** Can't find {json_file_path} provide a correct path")
            return []
        except ValueError:
            # Empty JSON file most likely due to abrupt killing of the process while writing
            return []

    else:
        try:
            obj_text = codecs.open(json_file_path, 'r', encoding='utf-8').read()
            return json.loads(obj_text)
        except FileNotFoundError:
            print(f"*** Can't find {json_file_path} provide a correct path")
            return []
        except Exception as e:
            # Empty JSON file most likely due to abrupt killing of the process while writing
            # print (e)
            return []


def go_through_dir(directory: str, filter_file_extension: str) -> List[str]:
    """ Goes through a directory and returns a list of file paths having the given file extension 
        Eg. fs.goThroughDir('/home/user/dir', '.json')
    """
    file_paths = []
    if not pathExists(directory):
        print("Directory {} does not exist".format(directory))
        return file_paths
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix == filter_file_extension:
                file_paths.append(os.path.join(root, file))
    return file_paths


def pathExists(path: str) -> bool:
    return os.path.exists(path)


def delete_directory(path: str) -> None:
    if pathExists(path):
        shutil.rmtree(path)


def writeJSONFile(data: Any, file_path: str) -> Any:
    try:
        # print("Writing JSON file "+file_path)
        json.dump(data, codecs.open(file_path, 'w', encoding='utf-8'),
                  separators=(',', ':'))
    except:
        print("Could not write to " + file_path)


def create_dir_list_if_not_present(paths: List) -> None:
    # Check of type of paths is list
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)


def writeFile(data: str, file_path: str) -> Any:
    f = open(file_path, "w+")
    f.write(data)
    f.close()


def getFileName(filepath: str) -> str:
    return os.path.basename(filepath)


def join(dir: str, filename: str) -> str:
    return os.path.join(dir, filename)


def mkdir(dirpath: str) -> None:
    try:
        os.mkdir(dirpath)
        # print("Directory ", dirpath,  " Created ")
    except FileExistsError:
        pass
        # print("Directory ", dirpath,  " already exists")


def get_all_empty_json_files(dirpath: str) -> List:
    list_of_files = go_through_dir(dirpath, '.json')
    empty_json_files = []
    for file in list_of_files:
        try:
            # file_loc = os.p.join(dirpath, file)
            with open(file) as json_file:
                content = json.load(json_file)
                if not len(content) > 0:
                    empty_json_files.append(file)
        except FileNotFoundError:
            print(
                "Please provide a correct file p. Eg. ./results/test.json")
        except ValueError:
            # Empty JSON file, most likely due to force killing of extraction process
            empty_json_files.append(file)
            # print("Removing empty file {}".format(file))
    # print("The directory contained {} files of which {} turned out to be empty".format(
    #     len(list_of_files), len(empty_json_files)))
    return empty_json_files


def read_file_content(fl: str) -> str:
    with open(fl, 'r') as f:
        content = f.read()
    return content


def sample_from_tar(tar_file_path: str, out_dir: str, file_extension_to_sample='.js',
                    required_number_of_files: int = -1):
    try:
        with TarFile(tar_file_path, "r") as tobj:
            file_list = tobj.getnames()
            random.shuffle(file_list)
            # if required_number_of_files > 0:
            #     file_list = file_list[:required_number_of_files]
            for f in tqdm(file_list,
                          desc='Sampling  files from {}'.format(tar_file_path)):
                if required_number_of_files == 0:
                    break
                if f.endswith(file_extension_to_sample):
                    tobj.extract(f, path=out_dir)
                    if required_number_of_files > 0:
                        required_number_of_files -= 1
    except Exception as e:
        print("Error reading/extracting {}".format(tar_file_path))


def sample_from_zip(zip_file_path: str, out_dir: str, file_extension_to_sample='.js',
                    required_number_of_files: int = -1) -> None:
    try:
        with ZipFile(zip_file_path, 'r') as zobj:
            file_list = zobj.namelist()
            random.shuffle(file_list)
            # if required_number_of_files > 0:
            #     file_list = file_list[:required_number_of_files]
            for f in tqdm(file_list, desc='Sampling files from {}'.format(zip_file_path)):
                if required_number_of_files == 0:
                    break
                if f.endswith(file_extension_to_sample):
                    zobj.extract(f, path=out_dir)
                    if required_number_of_files > 0:
                        required_number_of_files -= 1

    except BadZipFile:
        print("Can't read zip {}, it is probably broken".format(zip_file_path))


def copy_n_files_at_random(source_dir: str, dest_dir: str, extension: str, n_files: int) -> None:
    """
    Given a source and destination directory copy 'n' files of the
    particular extension from source to destination
    :param source_dir: The source directory
    :param dest_dir: The destination directory
    :param extension: Extension e.g. '.json'
    :param n_files: Number of files to copy
    :return:
    """
    if not pathExists(source_dir):
        print("Source directory does not exist")
        return
    create_dir_list_if_not_present([dest_dir])

    file_list = go_through_dir(source_dir, extension)
    random.shuffle(file_list)
    print("Copying {} files from {} to {} ".format(n_files, source_dir, dest_dir))
    if len(file_list) > n_files:
        files_to_copy = file_list[:n_files]
        # print(file_list)
        for file in files_to_copy:
            dest_link = os.path.join(dest_dir, os.path.basename(file))
            shutil.copyfile(file, dest_link)
    else:
        print("Not enough files to select from")


# Tests
if __name__ == '__main__':
    sample_from_tar(tar_file_path='benchmarks/data.tar.gz', out_dir='benchmarks', required_number_of_files=-1)
