Semantic Bug Seeding: A Learning-Based Approach for Creating Realistic Bugs 🐞
---

* Please find our artefact as archive : [zenodo](https://zenodo.org/record/4901843) 
* Becauce of space limitations, we do not include the required _benchmark_ folder. Please download it from the archive at zenodo.
## Requirements

- Node.js v14.17.0
- Python 3.8.5
- Ubuntu 20.04

Install **Node.js** and the required packages:

````shell
# You may install Node.js using nvm : https://github.com/nvm-sh/nvm
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
source ~/.bashrc

# Install Node.js 14
nvm install 14.17.0
# Install the required Node.js packages
npm install
````

Create a virtual environment for **Python** and install the required packages:

````shell
sudo apt install -y python3-dev # required for the 'fasttext' package
sudo apt install -y python3-venv

# Create a virtual environment
python3 -m venv semseed_venv
# Activate the virtual environment
source semseed_venv/bin/activate
# Install the required Python packages
pip install -r requirements.txt
````

We provide pre-trained token embeddings trained using fastText (https://fasttext.cc). The training has been performed
using JavaScript files obtained from https://www.sri.inf.ethz.ch/js150.

---

## 1. Obtain Patterns for Seeding Bugs

You may **skip** this step and use the patterns used in the paper available at
_benchmarks/bug_seeding_patterns_for_semantic_seeding.json_ for seeding bugs (Step 2).

Patterns can be obtained using two steps. The first step is to download all GitHub repositories, and the second step is
to go through the commits of the downloaded repos and select and save only certain commits and to extract patterns from
those commits.

### a) Download GitHub repositories

**Warning:** Downloading top-100 GitHub repositories will take large disk space.

The list of top GitHub JavaScript repositories is present at _benchmarks/top1000GithubRepos.json_ which is used by
default for downloading the repos. Alternatively, this list can be generated using the _getLinks()_ function from the
_bug_seeding/obtain_bug_seeding_patterns/main.js_ and setting the GitHub authentication (username, password) in the
file _bug_seeding/obtain_bug_seeding_patterns/repo_downloader/getTopGitHubRepoNames.js_.

Download repos present in _benchmarks/top1000GithubRepos.json_:

````shell
node bug_seeding/obtain_bug_seeding_patterns/repo_downloader/main.js
````

Tip 💡:
The default number of repos to be downloaded is 100 and default download directory is _benchmarks/top_JS_repos_ both of
which can be changed in _main.js_.

### b) Obtain seeding patterns from downloaded repositories

Assuming the repos have been downloaded in the default location i.e., _benchmarks/top_JS_repos_, the next step is to go
through each repo and save the commits.

How it works?

- For each repo, walk through the whole commit history starting from the most recent commit
- For each of the commits search the commit message for the presence of certain query terms
- If the query term exists, find a diff between the commit and its parent
- Go through each file in the diff and select only '.js' (JavaScript) files
- For each of these '.js' files, find single line changes and save both the 'new content' and the 'old content' along
  with their line numbers to a MongoDB database
- Extract patterns from the commits and save back to the database.

Saving commits require installation of MongoDB and the creation of a user with proper rights. The steps are follows:

#### Install & Setup MongoDB

````shell
# Install MongoDB Community Edition on Ubuntu 20.04
# Documentation -> https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu

wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# Once installation has finished start MongoDB
sudo systemctl start mongod
````

Now, we need to create a MongoDB user. To do so open the MongoDB shell using the command: ``mongo``

In the shell issue the following commands to creat a user and set the password.

````shell
use admin

db.createUser(
  {
    user: "semSeedUser",
    pwd: "semSeedPassWord124",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
  }
)
````

Tip 💡:
The default user is called _semSeedUser_ and the password is _semSeedPassWord124_. If you change the default username
and password, make sure to also edit _database_config.json_.

#### Go through commits and extract patterns

The next step is to go through the downloaded repos and extract commits where the commit message contains certain words
and then extract patterns from those commits. This can be done as follows:

```shell
python3 bug_seeding/obtain_bug_seeding_patterns/extract_bug_seeding_patterns_from_repos/main.py
```

Tip 💡:

- The directory where to look for the repositories and which 'hot-words' to look for in the commit message can be
  configured in _main.py_.
- The name of the database that is created, the name of the collection in database can be configured in  
  _database_config.json_.
- To check if _main.py_ worked, you may enter the mongo shell (using the command ``mongo`` in a terminal) and issue the
  following command. This will randomly select a commit saved in the database and display on the screen.

  ```shell
  use SemSeed_github_commits_db;
  db.commits.aggregate([{ $sample: { size: 1 } }]);
  ```

  Alternatively, the data can be viewed using MongoDB Compass. The download and install instruction can be found:
  https://docs.mongodb.com/compass/current/install

#### Write the patterns to a file

Once the patterns have been extracted and saved to the database, the aggregate patterns can be saved to a JSON file
using the following script:

````shell
python3 bug_seeding/obtain_bug_seeding_patterns/extract_bug_seeding_patterns_from_repos/aggregateChanges.py
````

Tip 💡:
The filepath of the JSON file can be configured in the same file.

---

## 2. Seed bugs using SemSeed

Given JavaScript files in _benchmarks/data_, seed bugs:

````shell
python3 bug_seeding/run_bug_seeding.py
````

Currently, the _benchmarks/data_ contains a sample JS file that may be used to test the implementation. Further JS files
can be downloaded for example from https://www.sri.inf.ethz.ch/js150 and extracted to the _data_ directory. The default
patterns used for seeding bugs is present in _benchmarks/bug_seeding_patterns_for_semantic_seeding.json_.

By default, the seeded bugs or the mutated JavaScript files can be found at
_benchmarks/js_benchmark_seeded_bugs_. Each JS file in the directory represents one seeded bug and is accompanied by a
JSON file that contains information about the seeded bug eg. where the bug has been seeded, which pattern has been used
etc .

Tip 💡:
If you want to use your own patterns, make sure to keep the format same.

---

## 3. Train DeepBugs

Train DeepBugs with datasets where the generated negative (buggy) examples have been created using either SemSeed or
using the default configuration of DeepBugs. The training data can be obtained by seeding bugs to the de-duplicated [2]
JavaScript files downloaded from https://www.sri.inf.ethz.ch/js150. The bug seeding patterns for both types of bugs can
be selected using the function
_select_particular_type_of_seeding_pattern()_ in the file _bug_seeding/run_bug_seeding.py_.

The validation datasets can be obtained from (refer to the paper for more information):

- The 8 of the held-out bugs
- Bugs gathered from 900 popular GitHub JavaScript projects which may be obtained by downloading the GitHub projects
  101-1000, mentioned in _benchmarks/top1000GithubRepos.json_.
- Bugs from the JavaScript variant of an existing dataset of single-statement bugs [1].

Tip 💡:
We provide pre-generated datasets for training and validating DeepBugs. Each of command given below for training
DeepBugs contains flags '--trainingData' & '--validationData' which refer to the file paths of pre-generated datasets.

### Wrong binary operands

Wrong binary operands, where a developer uses an incorrect operand in a binary expression, e.g., accidentally writing
``length * height`` instead of ``length * breadth``.

**Using SemSeed generated bugs:**

```shell
python3 DeepBugs/python/BugDetection.py IncorrectBinaryOperand --learn benchmarks/token_to_vector.json benchmarks/type_to_vector.json benchmarks/node_type_to_vector.json --trainingData benchmarks/full_dataset_wrong_binopnd.json --validationData benchmarks/correct_buggy_real_binops.json --SemSeed
```

**Using default DeepBugs**

```shell
python3 DeepBugs/python/BugDetection.py IncorrectBinaryOperand --learn benchmarks/token_to_vector.json benchmarks/type_to_vector.json benchmarks/node_type_to_vector.json --trainingData benchmarks/full_dataset_wrong_binOpnd_no_seeded_included.json --validationData benchmarks/correct_buggy_real_binops.json --Default
```

### Wrong assignments

Wrong assignment bugs, where the right hand side of an assignment is incorrect, e.g., writing ``i=o;`` instead of
``i=0;``.

**Using SemSeed generated bugs:**

````shell
python3 DeepBugs/python/BugDetection.py IncorrectAssignment --learn benchmarks/token_to_vector.json benchmarks/type_to_vector.json benchmarks/node_type_to_vector.json --trainingData benchmarks/full_dataset_wrong_assignment.json --validationData benchmarks/correct_buggy_real_wrong_assignments.json --SemSeed
````

**Using default DeepBugs**

````shell
python3 DeepBugs/python/BugDetection.py IncorrectAssignment --learn benchmarks/token_to_vector.json benchmarks/type_to_vector.json benchmarks/node_type_to_vector.json --trainingData benchmarks/full_dataset_wrong_assignment_no_seeded_included.json --validationData benchmarks/correct_buggy_real_wrong_assignments.json --Default
````

The evaluation of the DeepBugs predictions can be found at
_compare_real_bug_finding_ability/DeepBugs_prediction_evaluation.ipynb_

---

## 4. Comparison with Mutandis

The comparison with Mutandis can be found as a jupyter notebook at
_compare_real_bug_finding_ability/syntax_check_mutandis_compare.ipynb_

---

**References**

- [1]: How Often Do Single-Statement Bugs Occur? The ManySStuBs4J Dataset by Rafael-Michael Karampatsis & Charles Sutton
- [2]: The adverse effects of code duplication in machine learning models of code by Miltiadis Allamanis