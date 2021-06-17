"""
@author Jibesh Patra
"""

from mongoengine import *
import json
import codecs


def read_config(json_file_path):
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


db_config = read_config(json_file_path='database_config.json')

connect(db_config['database_name'], username=db_config['username'], password=db_config['password'],
        authentication_source='admin', host=db_config['host'], port=db_config['port'])


class QueryChanges(QuerySet):
    def get_abstracted_changes(self):
        pipeline = [
            {
                '$project': {
                    'single_line_changes': True,
                    'num_files_changed': True,
                    'num_single_line_changes': True,
                    'commit_hash': True,
                    'url': True,
                    'commit_time': True,
                    'local_repo_path': True
                }
            }, {
                '$match': {
                    'num_files_changed': 1,
                    'num_single_line_changes': 1
                }
            }, {
                '$unwind': {
                    'path': '$single_line_changes',
                    'preserveNullAndEmptyArrays': False
                }
            }, {
                '$match': {
                    'single_line_changes.analysis_report': 'success'
                }
            }, {
                '$addFields': {
                    'fix': '$single_line_changes.change_summary.fix',
                    'fix_tokenType': '$single_line_changes.new_file.change_analysis.type',
                    'fix_file_path': '$single_line_changes.new_file.path',
                    'fix_actual': '$single_line_changes.new_file.change_analysis.tokens',
                    'fix_range': '$single_line_changes.new_file.change_analysis.range',
                    'fix_line': '$single_line_changes.new_file.change_analysis.line',
                    'buggy': '$single_line_changes.change_summary.buggy',
                    'buggy_tokenType': '$single_line_changes.old_file.change_analysis.type',
                    'buggy_file_path': '$single_line_changes.old_file.path',
                    'buggy_actual': '$single_line_changes.old_file.change_analysis.tokens',
                    'buggy_range': '$single_line_changes.old_file.change_analysis.range',
                    'buggy_line': '$single_line_changes.old_file.change_analysis.line'
                }
            }, {
                '$project': {
                    'buggy': True,
                    'buggy_actual': True,
                    'buggy_file_path': True,
                    'buggy_tokenType': True,
                    'buggy_range': True,
                    'buggy_line': True,
                    'fix': True,
                    'fix_tokenType': True,
                    'fix_actual': True,
                    'fix_file_path': True,
                    'fix_range': True,
                    'fix_line': True,
                    'commit_time': True,
                    'local_repo_path': True,
                    'lessthanX_fix': {
                        '$lt': [
                            {
                                '$size': '$fix'
                            }, 20
                        ]
                    },
                    'lessthanX_buggy': {
                        '$lt': [
                            {
                                '$size': '$buggy'
                            }, 20
                        ]
                    },
                    'commit_hash': True,
                    'url': True
                }
            }, {
                '$match': {
                    'lessthanX_fix': True,
                    'lessthanX_buggy': True
                }
            }, {
                '$project': {
                    'lessthanX_fix': False,
                    'lessthanX_buggy': False
                }
            }, {
                '$sort': {
                    'commit_time': 1
                }
            }
        ]
        return self().aggregate(*pipeline)

    def get_fix_and_buggy_tokens(self, id_h):
        q = list(self(pk=id_h).only(
            'single_line_changes.old_file.change_analysis.tokens',
            'single_line_changes.new_file.change_analysis.tokens'))
        fixed_tokens = q[0]['single_line_changes'][0]['new_file']['change_analysis']['tokens']
        buggy_tokens = q[0]['single_line_changes'][0]['old_file']['change_analysis']['tokens']
        return {'actual_buggy_tokens': buggy_tokens, 'actual_fixed_tokens': fixed_tokens}


class Commits(Document):
    commit_id = StringField(primary_key=True)
    commit_hash = StringField(required=True)
    commit_message = StringField(required=True)
    commit_time = DateTimeField()

    local_repo_path = StringField()
    parent_hash = StringField()
    url = URLField()

    num_files_changed = IntField()

    single_line_changes = ListField(DictField(DictField()))
    num_single_line_changes = IntField()
    meta = {'queryset_class': QueryChanges}
