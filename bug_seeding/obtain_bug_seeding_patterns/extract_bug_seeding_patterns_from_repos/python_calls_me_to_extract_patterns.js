/*

@author Jibesh Patra

The python script extracts the files & commits that have single line changes in the commit.
This file extract patterns from the commits.
 */

const fs = require('fs');
const git = require('simple-git/promise');
const _ = require('lodash');
const ExtractSingleLineChangedNodes = require('./analyses/ExtractDataGivenNodes').ExtractSingleLineChangedNodes;
const assert = require('assert');
const dbconfig = require('../../../database_config.json');

/**
 * Given JavaScript code, perform static analysis on the code
 * @param code
 * @param nonTrackingNodes
 * @returns {(*|{})[]}
 */

function analyseCode(code, nonTrackingNodes) {
    assert.ok(Array.isArray(nonTrackingNodes)); // Should be an Array
    assert.ok(nonTrackingNodes.length > 0); // It should have at-least one Node to track

    let dataFromSpecificNodes = new ExtractSingleLineChangedNodes(code, nonTrackingNodes);

    let analysedCode = dataFromSpecificNodes.goThroughASTExtractSpecificNodes();
    for (let dt of analysedCode) {
        dataFromSpecificNodes.abstractIdentifiers(dt);
        dataFromSpecificNodes.abstractLiterals(dt);
    }

    return [analysedCode, dataFromSpecificNodes.scopeToIdentifier, dataFromSpecificNodes.scopeToLiteral, dataFromSpecificNodes.lineToTokenSequence];
}

/**
 * Given a commit, there could be many single line changes. This function will extract
 * only for a specific Node types.
 *
 * @param content{Array} - The content of a commit
 * */
async function extractSpecificNodes(content) {
    /**
     * It is not trivial to find out the Nodes that got changed in a single-line change.
     * As a result, we track all possible Nodes. We then match the line numbers and select
     * only the Node that  has the same line number as the changed line of code.
     */
    let nonTrackingNodes = [
        'Identifier',
        'Literal'
    ];

    for (let c = 0; c < content.length; c++) {
        let commit = content[0];
        let analysedData = [];

        // For all single line changes
        for (let single_line_change of commit.single_line_changes) {
            single_line_change.analysis_report = 'Not Analysed';

            // -------------------- Fixed file / New file ---------------------
            let fixed_file_content = await git(commit.local_repo_path).show([commit.commit_hash + ':' + single_line_change.new_file.path]);
            // Data about the given nodes in the bug-fixed file
            analysedData = analyseCode(fixed_file_content, nonTrackingNodes);
            let fixed_codeAnalysis = analysedData[0];
            if (fixed_codeAnalysis.length === 0) {
                single_line_change.analysis_report = 'fixed_File_not_parsable';
                continue;
            }
            // Select only the part of the analysis that got changed (part of the current single line change)
            let fixedSelectedNode = selectTheCorrectNode(fixed_codeAnalysis, single_line_change.new_file.line_num);
            let fixedTokenSequenceOfChangedLine = analysedData[3][single_line_change.new_file.line_num];

            if (Object.keys(fixedSelectedNode).length === 0 || fixedSelectedNode.tokens.length === 0) {
                single_line_change.analysis_report = 'fixed_Node_not_found';
                continue;
            }
            // Now add all Identifiers and Literals that belong to the file along with their respective 'scope'
            single_line_change.new_file['identifiers'] = analysedData[1];
            single_line_change.new_file['literals'] = analysedData[2];

            // ---------------------- Buggy file / Old file -----------------------
            let buggy_file_content = await git(commit.local_repo_path).show([commit.parent_hash + ':' + single_line_change.old_file.path]);
            // Data about the given nodes in the buggy file
            analysedData = analyseCode(buggy_file_content, nonTrackingNodes);
            let buggy_codeAnalysis = analysedData[0];
            if (buggy_codeAnalysis.length === 0) {
                single_line_change.analysis_report = 'buggy_File_not_parsable';
                continue;
            }
            // Only the Node
            let buggySelectedNode = selectTheCorrectNode(buggy_codeAnalysis, single_line_change.old_file.line_num);
            let buggyTokenSequenceOfChangedLine = analysedData[3][single_line_change.old_file.line_num];

            if (Object.keys(buggySelectedNode).length === 0 || buggySelectedNode.tokens.length === 0) {
                single_line_change.analysis_report = 'buggy_Node_not_found';
                continue;
            }
            // Now add all Identifiers and Literals that belong to the file along with their respective 'scope'
            single_line_change.old_file['identifiers'] = analysedData[1];
            single_line_change.old_file['literals'] = analysedData[2];

            /*
            If we compare the number of token differences between the actually buggy line and the fixed line then the
            it should be equal to the token difference between extracted buggy and fixed. If this is not so then
            we have not been able properly extract the change.
             */
            let tokenDifferenceInCommit = fixedTokenSequenceOfChangedLine.length - buggyTokenSequenceOfChangedLine.length;
            let tokenDifferenceInExtraction = fixedSelectedNode.tokens.length - buggySelectedNode.tokens.length;
            // -------------------------------------------------------
            // Sometimes the selected Nodes are wrong and do not actually represent the change.
            // There does not exist a single node that can capture the change
            // Eg. https://github.com/axios/axios/commit/c573a12b748dd50456e27bbf1fd3e6561cb0b3d2
            // https://github.com/strapi/strapi/commit/cc1669faf55ebd9b3029c4a03a7a5b06d8e5d71b
            if (_.isEqual(fixedSelectedNode.tokens, buggySelectedNode.tokens) || tokenDifferenceInCommit !== tokenDifferenceInExtraction) {
                single_line_change.analysis_report = 'neither_Node_not_found';
                continue;
            }

            // Fields added by our analysis
            single_line_change.analysis_report = 'success';
            single_line_change.old_file['change_analysis'] = buggySelectedNode;
            single_line_change.new_file['change_analysis'] = fixedSelectedNode;
            single_line_change['change_summary'] = renameAbstractedChanges(fixedSelectedNode, buggySelectedNode);
        }
        return commit.single_line_changes; // We only deal with one commit at a time. So we can return it here
    }

}


/**
 * It is possible that both the fixed and the buggy part of the conditional test contains the
 * same Identifiers. Since, we abstract the Identifiers independently, might need to be named properly.
 * Eg.
 *  Buggy →
 *          a < b && c < d gets abstracted as Idf_1 < Idf_2 && Idf_3 < Idf_4
 *  Fixed →
 *          a < c && r < d gets abstracted as Idf_1 < Idf_2 && Idf_3 < Idf_4
 * The proper renaming should be
 * Idf_1 < Idf_3 && Idf_5 < Idf_4
 *
 * @param {Object} fixed_conditional
 * @param {Object} buggy_conditional
 */
function renameAbstractedChanges(fixed_conditional, buggy_conditional) {
    // Remember, we want to understand how 'buggy' got 'fixed'
    let bug_fix_change = {
        fix: Array.from(fixed_conditional.abstractedTokens),
        buggy: Array.from(buggy_conditional.abstractedTokens),
        idf_mapping: {},
        lit_mapping: {}
    };


    /*
    Although mentioned above with the example of a 'buggy' to 'fix' renaming. We
    actually do not rename the 'fix' part and rather rename the 'Idf_' of the
    'buggy' part.
    We do this since we want to learn how to seed bugs and not how to fix them
    */
    for (let i = 0; i < fixed_conditional.tokenTypes.length; i++) {

        if (fixed_conditional.tokenTypes[i] === 'Identifier') {
            let idf_val = fixed_conditional.tokens[i];
            if (!{}.hasOwnProperty.call(bug_fix_change.idf_mapping, idf_val)) {
                bug_fix_change.idf_mapping[idf_val] = fixed_conditional.abstractedTokens[i];
            }
        } else if (fixed_conditional.tokenTypes[i] === 'Literal') {
            let lit_val = fixed_conditional.tokens[i];

            if (!{}.hasOwnProperty.call(bug_fix_change.lit_mapping, lit_val)) {
                bug_fix_change.lit_mapping[lit_val] = fixed_conditional.abstractedTokens[i];
            }
        }
    }

    for (let j = 0; j < buggy_conditional.tokenTypes.length; j++) {

        if (buggy_conditional.tokenTypes[j] === 'Identifier') {
            let idf_val = buggy_conditional.tokens[j];
            if ({}.hasOwnProperty.call(bug_fix_change.idf_mapping, idf_val)) {
                bug_fix_change.buggy[j] = bug_fix_change.idf_mapping[idf_val];
            } else {
                let abdstract_idf = 'Idf_' + (Object.keys(bug_fix_change.idf_mapping).length + 1);
                bug_fix_change.buggy[j] = abdstract_idf;
                bug_fix_change.idf_mapping[idf_val] = abdstract_idf;
            }
        } else if (buggy_conditional.tokenTypes[j] === 'Literal') {
            let lit_val = buggy_conditional.tokens[j];
            if ({}.hasOwnProperty.call(bug_fix_change.lit_mapping, lit_val)) {
                bug_fix_change.buggy[j] = bug_fix_change.lit_mapping[lit_val];
            } else {
                let abstract_lit = 'Lit_' + (Object.keys(bug_fix_change.lit_mapping).length + 1);
                bug_fix_change.buggy[j] = abstract_lit;
                bug_fix_change.lit_mapping[lit_val] = abstract_lit;
            }
        }
    }

    bug_fix_change.idf_mapping = _.invert(bug_fix_change.idf_mapping);
    bug_fix_change.lit_mapping = _.invert(bug_fix_change.lit_mapping);

    return bug_fix_change;
}


/**
 * A commit may have many single line changes.  This function
 * filters out only the code location that matches the line number.
 * Once all Nodes, belonging to the changed line is found, select
 * the node having maximum tokens
 * @param allCodeLocations{Object}
 * @param changedLineNum{number}
 * @return {Object}
 */
function selectTheCorrectNode(allCodeLocations, changedLineNum) {
    // Candidate Nodes have the same line number as that of the changed line numer
    let candidateNodes = [], candidateNodesNumToks = [];

    changedLineNum = parseInt(changedLineNum);

    for (let curNode of allCodeLocations) {
        let c_lineStart = parseInt(curNode.line.split('-')[0]);
        let c_lineEnd = parseInt(curNode.line.split('-')[1]);

        // First check if a Node only spans single line. If it does not, ignore
        if (c_lineStart !== c_lineEnd) continue;
        // Also, if the changed line number is not same as node's line number, ignore
        if (changedLineNum !== c_lineStart) continue;

        candidateNodes.push(curNode);
        candidateNodesNumToks.push(curNode.tokens.length);
    }

    if (candidateNodes.length === 0) return {};

    // Once, we have all the Nodes that belongs to the changed line. We select the Node that best expresses it.
    // Note: There is no guarantee that this is the correct Node. This is simply an approximation.
    let max = Math.max(...candidateNodesNumToks);
    return candidateNodes[candidateNodesNumToks.indexOf(max)];
}

function writeExtractedData(data, outFilePath) {
    fs.writeFileSync(outFilePath, JSON.stringify(data));
    console.log(`Wrote the results to ${outFilePath}`);
}

async function main(inFile, outDir) {
    try {
        let conditionals = await extractSpecificNodes(inFile);
        // console.log(conditionals);

        if (conditionals.length > 0) {
            writeExtractedData(conditionals, outDir, inFile);
        }
    } catch (e) {
        console.log(e);
    }
}

function parse_cli_arguments() {
    const ArgumentParser = require('argparse').ArgumentParser;
    let parser = new ArgumentParser({
        version: '0.0.1',
        addHelp: true,
        description: 'Go through single line changes and extract \'only\' certain the nodes'
    });

    parser.addArgument(
        ['-commitId'], {
            help: 'Specify the commit id'
        });

    let args = parser.parseArgs();
    return {
        'commitId': args.commitId
    }
}

/**
 * Given  a commitId extract data
 * @param {String} commitId
 */
async function extractData(commitId) {
    const MongoClient = require('mongodb').MongoClient;
    const url = `mongodb://${dbconfig.username}:${dbconfig.password}@${dbconfig.host}:${dbconfig.port}`;
    // console.log(url);
    const dbName = dbconfig.database_name;

    const client = new MongoClient(url, {
        useNewUrlParser: true,
        useUnifiedTopology: true
    });

    client.connect(function (err) {
        assert.strictEqual(null, err);
        // console.log("Connected successfully to server");
        const collection = client.db(dbName).collection(dbconfig.collection_name);

        let query = {
            _id: commitId
        };


        // First query the database and find the correct commit
        collection.find(query).toArray(async function (err, items) {
            let singleLineChanges = await extractSpecificNodes(items);
            // Once the updated, single line changes are available. Add them
            collection.updateOne({
                    _id: commitId
                }, {
                    $set: {
                        single_line_changes: singleLineChanges
                    }
                },
                {},
                function (err, res) {
                    // console.log(res);
                    // console.log(err);
                    client.close();
                }
            );
        });
    });

}

(
    async function () {
        let {
            commitId
        } = parse_cli_arguments();
        if (commitId)
            await extractData(commitId);
    }
)();
