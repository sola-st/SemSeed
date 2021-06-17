/**
 * Contains utility methods for file and folder operations
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

/**
 * Check if the p is a directory
 * @param {string} path
 * @returns {boolean}
 */
function isDir(path) {
    try {
        fs.accessSync(path, fs.constants.R_OK);
    } catch (err) {
        console.error(`\n\n##### ----- No access to ${path} ----- ######\n\n`);
        return false;
    }
    return fs.statSync(path).isDirectory();
}

/**
 * Check if a file exists and is available to be read
 * @param {string} filePath
 * @returns {boolean}
 */
function available(filePath) {
    return fs.existsSync(filePath);
    try {
        fs.accessSync(path, fs.constants.R_OK);
    } catch (err) {
        return false;
    }

    return true;
}

/**
 * Given a p, returns the extension of the p in lowercase
 * @param {string} filePath
 * @returns {string}
 */
function getExtension(filePath) {
    assert.ok(!isDir(filePath));
    return path.extname(filePath).toLowerCase();
}

/**
 * Read a file and returns the content of the file. If the filetype
 * is JSON then also converts to a JSON object.
 * If there is parsing error or for some reason, the file could not be read
 * then returns null
 * @param {string} filePath Path of the file that needs to be read
 * @returns {(null|string|Object.<string,string>)}
 */
function getFileContent(filePath) {
    let content;
    // assert.ok(!isDir(filePath));
    // assert.ok(available(filePath));
    if (isDir(filePath) || !available(filePath))
        return null;
    try {
        content = fs.readFileSync(filePath, 'utf8');
        if (getExtension(filePath) === '.json') content = JSON.parse(content);
    } catch (error) {
        content = null;
    }

    return content;
}

/**
 * Check if a file is accessible and then returns the size
 * of the file in bytes
 * @param {string} filePath
 * @returns {number}
 */
function getFileSize(filePath) {
    assert.ok(available(filePath));
    return fs.statSync(filePath).size;
}

/**
 * Go through a directory and all sub directories and create a list
 * links to the files in the particular directory.
 * @param {string} dirPath Initial p of a directory
 * @param {string} fileExtension Types of file
 * @returns {Array.<string>} List of files
 */
function createLinksOfFiles(dirPath, fileExtension) {
    /**
     * @type{string[]}
     */
    let fileList = [];
    let folderToTraverse = [dirPath];
    if (!fileExtension) throw 'Need extension of file that will be filtered';
    while (folderToTraverse.length !== 0) {
        let currentFolder = folderToTraverse.pop();
        let list_of_files_and_folders = fs.readdirSync(currentFolder);
        list_of_files_and_folders.forEach((f_path) => {
            let complete_path = path.join(currentFolder, f_path);
            if (isDir(complete_path))
                folderToTraverse.push(complete_path);
            else if (getExtension(complete_path) === fileExtension)
                fileList.push(complete_path);
        });
    }
    return fileList;
}

module.exports.available = available;
module.exports.getFileContent = getFileContent;
module.exports.getExtension = getExtension;
module.exports.getFileSize = getFileSize;
module.exports.createLinksOfFiles = createLinksOfFiles;