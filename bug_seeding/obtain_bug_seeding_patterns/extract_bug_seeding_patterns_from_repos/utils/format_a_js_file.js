/**

 Created on 16-April-2020
 @author Jibesh Patra

 Given a JavaScript file, remove comments and format it. The reason we do this is to
 seed bugs to a known format so that we can map the locations of the seeded bug later.

 Since we use a token sequence to seed bugs, comments and spaces in code messes up the
 location of the seeded bug. Once we re-generate the file with seeded bug, the original
 locations where the bug was seeded is hard to map back.
 **/


const fs = require('fs');
const fileops = require('./fileoperations');
const ArgumentParser = require('argparse').ArgumentParser;
const esprima = require('esprima');
const escodegen = require('escodegen');
const beautify = require('js-beautify').js,
    strip = require('strip-comments');
const UglifyJS = require("uglify-js");

function parse_cli_arguments() {
    let parser = new ArgumentParser({
        version: '0.0.1',
        addHelp: true,
        description: 'Take a JS file and format it and remove comments'
    });

    parser.addArgument(
        ['-inFile'], {
            help: 'The JavaScript file that needs to be formatted'
        });
    let args = parser.parseArgs();
    return {
        'inFile': args.inFile,
    }
}

/**
 * Given a file path, re-format it
 * @param{String} inFilePath
 */
function formatJSfile(inFilePath) {
    if (!fileops.available(inFilePath)) {
        // console.log(`${inFilePath} is not available`)
        return;
    }
    try {
        let code = fs.readFileSync(inFilePath, 'utf8');
        code = strip(code); // Remove comments from code
        let ast = {};
        try {
            ast = esprima.parseScript(code, {tokens: true});
        } catch (e) {
            try {
                ast = esprima.parseModule(code, {tokens: true});
            } catch (e) {
                ast = {}
            }
        }
        let tokens = [];
        for (let tok of ast.tokens) {
            tokens.push(tok.value);
        }

        code = tokens.join(' ');
        let formattedCode = beautify(code, {
            "indent_empty_lines": false,
            "break_chained_methods": false,
            "space_after_anon_function": false,
            "space_in_paren": false
        });
        let options = {
            compress: false,
            mangle: false,
            output: {
                beautify: true
            }
        };
        fs.writeFileSync(inFilePath, formattedCode);
        // console.log(code);
        // let uglify_format = UglifyJS.minify(formattedCode, options);
        // if (uglify_format.hasOwnProperty('error')) { // uglify does not support es6 and above
        //     fs.writeFileSync(inFilePath, formattedCode);
        // } else {
        //     fs.writeFileSync(inFilePath, uglify_format['code']);
        // }
        // console.log(`Pretty printing ${inFilePath}`);
    } catch (e) {
        // console.log(e);
    }
}

function formatFilesInDir(inDir) {
    let filePaths = fileops.createLinksOfFiles(inDir, '.js');
    filePaths.forEach(fl => {
        formatJSfile(fl);
    });
}

// Test ---
// (
//     function () {
//         let {
//             inFile
//         } = parse_cli_arguments();
//         // formatFilesInDir(inFile);
//         formatJSfile(inFile);
//     }
// )();


module.exports.formatJSfile = formatJSfile;
