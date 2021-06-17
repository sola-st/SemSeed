"""

Created on 25-March-2020
@author Jibesh Patra

"""

from bug_seeding_approaches.SeedBugs import SeedBugs
from typing import List


class SyntacticSeedBugs(SeedBugs):
    def __init__(self, bug_seeding_pattern: dict, target_location: dict, file_path: str):
        super().__init__(bug_seeding_pattern, target_location, file_path)

    def is_matching_token_sequence(self) -> bool:
        target = self.target_location
        seeding_pattern = self.bug_seeding_pattern

        # We only need to check syntactic matches
        if target['abstractedTokens'] != seeding_pattern['fix']:
            return False
        else:
            return True

    def apply_pattern(self) -> List[List]:
        
        return []
