"""
@author Jibesh Patra
"""

import subprocess
from threading import Timer
import os
import json
import multiprocessing
from multiprocessing import Pool
from tqdm import tqdm


def callNodeJS(argument):
    '''
    Call Node.js for each commit and create patterns.
    @param argument: Each argument is a commit id
    @return:
    '''
    path_to_process = os.path.join(os.path.normpath(
        os.getcwd() + os.sep), 'bug_seeding', 'obtain_bug_seeding_patterns', 'extract_bug_seeding_patterns_from_repos',
        'python_calls_me_to_extract_patterns.js')
    time_out_before_killing = 180  # seconds 180 -> 3 minutes
    try:
        def kill_process(p):
            return p.kill()

        p = subprocess.Popen(['node', path_to_process, '-commitId', argument],
                             stdout=subprocess.PIPE)
        time_out = Timer(time_out_before_killing, kill_process, [p])
        try:
            time_out.start()
            stdout, stderr = p.communicate()
            # print(stdout, stderr)
        finally:
            time_out.cancel()
    except subprocess.TimeoutExpired:
        # p.kill()
        pass


def create_patterns_from_commits(select_num_of_commits=-1):
    '''
    Query the MongoDB database and select only those commits (commit_ids) where the number of files
    changed is one and the changes are single line changes.

    Next, the CallNodeJS for only those commits and create patterns.

    @param select_num_of_commits: -1 means select all commits.
    @return:
    '''
    from database import GitHubCommits as db

    # query filters
    num_of_files_changed = 1
    num_single_line_changes = 1
    query_obj = db.Commits.objects(
        num_files_changed=num_of_files_changed, num_single_line_changes=num_single_line_changes)
    print('Found %d records that has only %d file change and only %d single line change' %
          (query_obj.count(), num_of_files_changed, num_single_line_changes))
    pks = json.loads(query_obj.only('pk').to_json())  # get only the primary keys

    # Now put all primary keys in a list.
    # The primary keys are nothing but commit hashes concatenated with the repository
    commit_ids = []

    for pk in pks:
        commit_ids.append(pk['_id'])

    if select_num_of_commits > 0:
        print("Selecting only %d commits of %d available commits" %
              (select_num_of_commits, len(commit_ids)))
        commit_ids = commit_ids[:select_num_of_commits]

    # Parallel execution
    with Pool(processes=multiprocessing.cpu_count()) as p:
        with tqdm(total=len(commit_ids)) as pbar:
            pbar.set_description_str(
                desc="Extracting Patterns ", refresh=False)
            for i, _ in tqdm(enumerate(p.imap_unordered(callNodeJS, commit_ids))):
                pbar.update()
            p.close()
            p.join()
