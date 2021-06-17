"""
@author Jibesh Patra

Aggregate the patterns and write to a JSON files.
"""

from utils import fileutils as fs


def write_bug_seeding_patterns_to_file(agg_data_out_file):
    from database import GitHubCommits as db
    abstract_changes = list(db.Commits.objects.get_abstracted_changes())
    changes_across_all_repos = []

    for change_summary in abstract_changes:
        change_summary['commit_time'] = change_summary['commit_time'].strftime("%d/%m/%Y, %H:%M:%S")
        cfx_actual = [str(e) for e in change_summary['fix_actual']]
        change_summary['fix_actual'] = cfx_actual

        cfb_actual = [str(e) for e in change_summary['buggy_actual']]
        change_summary['buggy_actual'] = cfb_actual

        changes_across_all_repos.append(change_summary)

    print(f'Writing data to {agg_data_out_file}')
    fs.writeJSONFile(changes_across_all_repos, agg_data_out_file)


if __name__ == "__main__":
    write_bug_seeding_patterns_to_file(agg_data_out_file='benchmarks/bug_seeding_patterns.json')
