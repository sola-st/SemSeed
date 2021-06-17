/*
1. This script uses GitHub API to get the top 'N' GitHub repositories and saves it in a file.
2. It then goes through this list and downloads each repo locally

@author Jibesh Patra
*/
const Scrapper = require('./getTopGitHubRepoNames').Scrapper;
const download = require('./downloadTopGithubRepos').download_repositories;
const path = require('path');
const fs = require('fs');
const fileutils = require('./fileoperations');

async function getLinks(link_to_top_repos, numOfGitHubRepos) {
    // Uncomment the following lines if top1000GithubRepos.json is not present OR needs to be updated

    // let github_scapper = new Scrapper(link_to_top_repos, numOfGitHubRepos);
    // // If more than '100' is required then the pages need to be changed for each request
    // github_scapper.getRepositoriesParseCommits({
    //   language: 'javascript',
    //   page: 1,
    //   q_no: 0
    // });
}

/**
 *
 * @param link_to_top_repos
 * @param download_dir
 * @param numOfGitHubRepos
 */
async function getLinksAndDownload(link_to_top_repos, download_dir, numOfGitHubRepos) {
    // 1. Get the links to the top 100 GitHub repositories
    getLinks(link_to_top_repos, numOfGitHubRepos).then(() => {
        // 2. Download some/all of them
        download(link_to_top_repos, numOfGitHubRepos, download_dir);
    });
}

function main() {

    let link_to_top_repos = path.join('benchmarks', 'top1000GithubRepos.json'); // Where the links (GitHub URLs) to top 'N' repos will be saved
    let download_dir = path.join('benchmarks', 'top_JS_repos'); // Where the top 'N' repos will be saved
    let num_of_github_repos_to_download = 100;

    if (!fileutils.available(download_dir))
        fs.mkdirSync(download_dir);

    getLinksAndDownload(link_to_top_repos, download_dir, num_of_github_repos_to_download).then(() => {
        console.log("Download ..");
    });
}

main();
