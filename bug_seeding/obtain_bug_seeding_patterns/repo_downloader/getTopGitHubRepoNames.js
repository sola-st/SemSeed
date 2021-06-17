/**
 * Use the GitHub query to first get the most popular JavaScript assignments according to the
 * number of stars.
 * Save the name of the repo and the GitHub link.
 *
 * @author Jibesh Patra
 */
const Octokit = require('@octokit/rest');
const path = require('path');
const fileutils = require('./fileoperations');

const fs = require('fs');

class Scrapper {
    constructor(outfile, top_n) {
        this.octokit = new Octokit(
            {
                'auth': {
                    username: 'SET_USERNAME',
                    password: 'SET_PASSWORD'
                }
            }
        );
        this.outfile = path.join(process.cwd(), outfile);
        this.top_n = top_n;

    }

    async getRepositoriesParseCommits({language, page, q_no}) {
        console.log("---------------- Current page --------------", page);
        let query = ['fix', 'bug', 'error', 'issue', 'squash'];
        let topJSrepos = [];
        try {
            /**
             * Search for repositories of a particular language.
             */
            const result = await this.octokit.search.repos({
                q: language,
                sort: 'stars',
                order: 'desc',
                per_page: this.top_n, // max → 100
                page: page // The page number of the result. We may iterate over page to get more result
            });

            if (result.status === 200) {
                let available_repos = result.data.total_count;

                console.log(`Got ${result.data.items.length} JavaScript repositories on page ${page}`);
                for (let i = 0; i < result.data.items.length; i++) {
                    let repo_name = result.data.items[i].full_name;

                    let repo = result.data.items[i];
                    topJSrepos.push({'clone_url': repo.clone_url, 'ssh_url': repo.ssh_url});
                    // let sshUrl = repo.ssh_url;
                    // console.log(repo.clone_url);
                    // console.log(repo.ssh_url);

                    // let commit_search_page = 1;
                    // const commit_search_result = await this.octokit.search.commits({
                    //     // The query searches for all commits that include the words 'fix' and 'bug' and 'error' and 'issue' in its message
                    //     q: query[q_no] + 'repo:' + repo_name,
                    //     per_page: 100, // max → 100
                    //     page: commit_search_page
                    // });
                    // if (commit_search_result.status === 200) {
                    //     let available_commits = commit_search_result.data.total_count;
                    //     let commit_data = commit_search_result.data.items;
                    //     console.log(`\tAvailable commits ${available_commits} for query ${query[q_no]}, Selecting ${commit_data.length} commits`);

                    //     for (let i = 0; i < commit_data.length; i++) {
                    //         let cmt_meta_info = commit_data[i];
                    //         let commit_message = cmt_meta_info.commit.message;
                    //         let commit_sha = cmt_meta_info.sha;
                    //         let repo_name = cmt_meta_info.repository.name;
                    //         let repo_owner = cmt_meta_info.repository.owner.login;

                    //         let getcommit_from_sha = await this.octokit.repos.getCommit(
                    //             {
                    //                 commit_sha: commit_sha,
                    //                 repo: repo_name,
                    //                 owner: repo_owner,
                    //             }
                    //         );

                    //         if (getcommit_from_sha.status === 200) { // If the commit is found
                    //             // console.log(getcommit_from_sha.data.stats);
                    //             let changed_files = getcommit_from_sha.data.files;
                    //             console.log(`\t${changed_files.length} files were involved in this commit`);
                    //             changed_files.forEach(commit_obj => {
                    //                 let filename = commit_obj.filename;
                    //                 /**
                    //                  * status can be added, removed, modified, renamed
                    //                  * added → The file was added during this commit
                    //                  * removed → similar
                    //                  * modified → The file was modified
                    //                  * renamed → The file was renamed
                    //                  */
                    //                 let status = commit_obj.status;
                    //                 // If JavaScript file and the file has been modified
                    //                 if (p.parse(filename).ext === '.js' && status === 'modified') {
                    //                     commit_obj['repo_name'] = repo_name;
                    //                     commit_obj['repo_owner'] = repo_owner;
                    //                     commit_obj['commit_sha'] = commit_sha;
                    //                     commit_obj['commit_message'] = commit_message;
                    //                     this.save_commits(commit_obj)

                    //                 } else {
                    //                     // console.log("Not js file");

                    //                 }
                    //             });
                    //         }

                    //     }

                    // }

                }

                let outfile = this.outfile;
                let out = [];
                if (fileutils.available(outfile))
                    out = JSON.parse(fs.readFileSync(outfile, 'utf8'));

                for (let rep of topJSrepos) {
                    out.push(rep);
                }
                console.log("Writing to " + outfile);

                fs.writeFileSync(outfile, JSON.stringify(out));
                // console.log("Waiting before going to the next page....");
                // ++page;
                // if (page > 10) // Top 100 repositories
                // {
                //     ++q_no;
                //     process.exit(1);
                // }
                // if (q_no >= query.length)
                //     process.exit(1);

                // setTimeout(() => { this.getRepositoriesParseCommits({ language: 'javascript', page: page, q_no: q_no }) }, 15000);
            }
        } catch (err) {
            console.log("Could not process request " + err);
            let rate_limit = await this.octokit.rateLimit.get();
            console.log(`The search rate limit is ${rate_limit.data.resources.search.remaining}`);
            console.log(`The search rate limit will reset at ${rate_limit.data.resources.search.reset}`);
            let remaining_time = rate_limit.data.resources.search.reset - Math.floor(Date.now() / 1000);
            remaining_time = remaining_time * 1000 + 10;

            // if (page < 200) {
            //     setTimeout(() => { this.getRepositoriesParseCommits({ language: 'javascript', page: page + 1 }) }, remaining_time);
            // }
        }
    }


    // save_commits(commit_obj) {
    //     if (commit_obj.hasOwnProperty('repo_owner') && commit_obj.hasOwnProperty('repo_name')) {
    //         let dirpath = p.join('results', commit_obj.repo_owner, commit_obj.repo_name);

    //         let json_filepath = p.join(dirpath, p.parse(commit_obj.filename).name + '_' + commit_obj.commit_sha.slice(commit_obj.commit_sha.length - 6) + '.json');

    //         fs.mkdir(dirpath, { recursive: true }, (err) => {
    //             if (err) throw err;
    //             fs.writeFile(json_filepath, JSON.stringify(commit_obj), (err) => {
    //                 if (err) throw err;
    //                 console.log(`File ${json_filepath} has been written`);
    //             })
    //         })
    //     }
    // }
}

// let scrapper = new Scrapper()

// // pages = 500
// // for (i = 24; i < pages; i++)
// 

module.exports.Scrapper = Scrapper;