/**
 * @author Jibesh Patra
 */

const fs = require('fs');
const git = require('simple-git');

/**
 *
 * @param {String} filePath
 * @param {Number} noOfRepos
 */
function readRepoNames(filePath, noOfRepos) {
    let repos = JSON.parse(fs.readFileSync(filePath));
    console.log(`\nFound ${repos.length} repositories, will download ${noOfRepos}`);
    return repos.slice(0, noOfRepos);
}

/**
 *
 * @param {Array<String>} repos
 * @param {String} directory
 */
async function cloneSelectedRepos(repos, directory) {
    let clone_tasks = [];
    const sleep = (milliseconds) => {
        return new Promise(resolve => setTimeout(resolve, milliseconds))
    }

    let all = repos.length;
    repos.forEach((repo) => {
        console.log(`Cloning ${repo.clone_url}`);
        clone_tasks.push(git(directory).clone(repo.clone_url).exec(() => {
            console.log(`Done cloning ${repo.clone_url} remaining ${--all}`);
        }));
        clone_tasks.push(sleep(1000));
    });
    try {
        let t = await Promise.all(clone_tasks);
    } catch (err) {
        console.log(err);

    }

}

/**
 *
 * @param {String} linkOfRepos
 * @param {Number} numOfRepoToDownload
 * @param {String} outDir
 */
function download_repositories(linkOfRepos, numOfRepoToDownload, outDir) {
    let repos = readRepoNames(linkOfRepos, numOfRepoToDownload);
    console.log("Writing the downloaded repositories to ==> " + outDir);
    cloneSelectedRepos(repos, outDir);
}

module.exports.download_repositories = download_repositories;
