"""
@author Jibesh Patra

This script goes through the top 'N' GitHub repositories already downloaded locally and finds single line changes.
Make sure to download the top 'N' repositories before running this script.

"""
import pygit2 as git
import utils.fileutils as fs
from os import listdir
import os
import multiprocessing
from os.path import isfile, join
import tqdm
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE
from parsepatch.patch import Patch
import re
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool
from tqdm import tqdm
from typing import List
from callNodeJSExtractData import create_patterns_from_commits


def get_git_repos_file_paths(source_dir):
    '''

    @param source_dir:
    @return:
    '''
    dir_list = listdir(source_dir)
    repo_paths = []
    for path in dir_list:
        if not isfile(path):
            repo_paths.append(join(source_dir, path))
    return repo_paths


def query_repo_save_commits(repo_path: str, query_terms: List, file_extension: str) -> None:
    '''

    @param repo_path:
    @param query_terms:
    @param file_extension:
    @return:
    '''
    from database import GitHubCommits as db

    repo = git.Repository(repo_path)
    remote_url = None
    for r in repo.remotes:
        remote_url = r.url.split('.git')[0]

    def file_filter(file_path):
        return file_path.endswith(file_extension)

    last_commit = None
    for l in repo.head.log():
        last_commit = l.oid_new
    # Go through each commit starting from the most recent commit
    for commit in repo.walk(last_commit, GIT_SORT_TOPOLOGICAL | GIT_SORT_REVERSE):
        num_parents = len(
            commit.parents)  # Do not want to include merges, hence we check if the number of parents is 'one'
        if num_parents == 1 and commit_message_contains_query(commit.message, query_terms):
            # Diff between the current commit and its parent
            diff = repo.diff(commit.hex + '^', commit.hex)
            changes = extract_single_line_changes(diff, file_filter)

            if len(changes) > 0:
                cm = db.Commits(
                    commit_id=remote_url.split('https://github.com/')[1] + '_' + commit.hex,
                    commit_hash=commit.hex,
                    commit_message=commit.message,
                    commit_time=datetime.fromtimestamp(commit.commit_time),
                    local_repo_path=repo_path,
                    parent_hash=str(commit.parent_ids[0]),
                    url=f'{remote_url}/commit/{commit.hex}',
                    num_files_changed=diff.stats.files_changed,
                    single_line_changes=changes,
                    num_single_line_changes=len(changes)
                )
                cm.save()  # Save the commit to the database


def extract_single_line_changes(diff, file_filter):
    """
    Given a diff and a file extension filter. Extract only single line changes.
    This function extracts only those commits where exactly one line has changed.
    :param diff:
    :param file_filter:
    :return:
    """
    single_line_changes = []
    if diff.stats.files_changed > 1:
        return []
    if diff.stats.deletions > 1 or diff.stats.insertions > 1:
        return []
    for patch in diff:
        # In most cases, the file paths remain the same
        old_file_path = patch.delta.new_file.path
        new_file_path = patch.delta.old_file.path

        # Parse the patch and also select only those files that have the required file extension
        try:
            parsed_patch = Patch.parse_patch(
                patch.text, file_filter=file_filter)
            line_numbers = get_changes_from_new_file(parsed_patch)
            # If more than one line has changed in the 'new'/'fixed' file, we ignore the commit.
            if new_file_path not in line_numbers or len(line_numbers[new_file_path]) > 1:
                return []
        except IndexError:
            continue

        # Once we have got the line number from the 'new' file, we get the line numbers from the 'old' file
        for hunk in patch.hunks:
            lines = hunk.lines
            for idx, lin in enumerate(lines):
                if new_file_path in line_numbers and lin.new_lineno in line_numbers[new_file_path]:
                    single_line_changes.append({
                        'old_file':
                            {
                                'path': old_file_path,
                                'line_num': lines[idx - 1].old_lineno,
                                'changed_line': lines[idx - 1].content
                            },
                        'new_file': {
                            'path': new_file_path,
                            'line_num': lin.new_lineno,
                            'changed_line': lin.content
                        }
                    })
    return single_line_changes


def get_changes_from_new_file(parsed_patch):
    '''

    @param parsed_patch:
    @return:
    '''
    single_changes_line_numbers = {}
    for file in parsed_patch:
        single_changes_line_numbers[file] = []
        if 'touched' in parsed_patch[file] and 'added' in parsed_patch[file] and 'deleted' in parsed_patch[file]:
            # List of line numbers
            touched_lines = parsed_patch[file]['touched']
            added_lines = parsed_patch[file]['added']  # List of line numbers
            # List of line numbers
            deleted_lines = parsed_patch[file]['deleted']
        else:
            continue

        if len(touched_lines) > 0:
            for line in touched_lines:
                next_line = line + 1
                prev_line = line - 1
                if next_line not in added_lines and next_line not in touched_lines and prev_line not in touched_lines:
                    single_changes_line_numbers[file].append(
                        line)  # The line number is always the '+' line number in the new file
    return single_changes_line_numbers


def commit_message_contains_query(message, query_terms):
    """
    Check if the commit message contains the query terms
    @param message: The commit message
    @param query_terms: The terms that we look for in the message
    @return:
    """
    tester = r'\b(' + '|'.join(query_terms) + ')'
    has_refactor_string = r'\b(refactor)'
    return bool(re.search(tester, message, re.IGNORECASE)) and not bool(
        re.search(has_refactor_string, message, re.IGNORECASE))


def extract_from_repo(arguments):
    repo_path, query_terms, file_extension = arguments
    query_repo_save_commits(repo_path, query_terms, file_extension)


def write_extracted_commits(data, outdir, repo_path):
    out_name = os.path.join(outdir, Path(repo_path).name + '.json')
    fs.writeJSONFile(data=data, file_path=out_name)


def parse_repos_extract_changes(git_repo_location, file_extension, query_terms,
                                num_of_repos_to_parse=-1):
    repo_paths = get_git_repos_file_paths(git_repo_location)
    debug = False  # Disable multiprocessing if debug is True
    if num_of_repos_to_parse > 0:
        print('Selecting %d repos out of %d available repos ' %
              (num_of_repos_to_parse, len(repo_paths)))
        repo_paths = repo_paths[:num_of_repos_to_parse]

    arguments = [(repo_path, query_terms, file_extension)
                 for repo_path in repo_paths]
    if not debug:
        with Pool(processes=multiprocessing.cpu_count()) as p:
            with tqdm(total=len(repo_paths)) as pbar:
                pbar.set_description_str(
                    desc="Parsing repos ", refresh=False)
                for i, _ in tqdm(
                        enumerate(
                            p.imap_unordered(extract_from_repo,
                                             arguments))):
                    pbar.update()
                p.close()
                p.join()
    else:
        for _ in enumerate(map(extract_from_repo, arguments)):
            pass


if __name__ == "__main__":
    top_JS_repos_path = os.path.join('benchmarks', 'top_JS_repos')
    terms_to_search_in_commit_message = ['Bug', 'Fix', 'Error', 'Issue', 'Problem', 'Correct']

    print("Make sure MongoDB is running. On Ubuntu, you may use 'sudo systemctl start mongod' ")

    # Extract and save all single line changes from the repos to the MongoDB database
    parse_repos_extract_changes(git_repo_location=top_JS_repos_path,
                                file_extension='.js', query_terms=terms_to_search_in_commit_message,
                                num_of_repos_to_parse=100)

    # After this has finished, call Node.js and create bug-seeding patterns.
    create_patterns_from_commits(select_num_of_commits=-1)
