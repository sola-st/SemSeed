const ExtractSingleLineChangedNodes = require('./analyses/ExtractDataGivenNodes').ExtractSingleLineChangedNodes;
const fs = require('fs');
const assert = require('assert');
const format_file = require('./utils/format_a_js_file').formatJSfile;

function analyseCode(code, nonTrackingNodes, trackingNodes) {
    if (code.length === 0) return {};
    assert.ok(Array.isArray(nonTrackingNodes)); // Should be an Array
    assert.ok(nonTrackingNodes.length > 0); // It should have atleast one Node to track

    // Number of tokens to extract around each Identifier and also the number of tokens
    // to extract around each point of interest Eg. conditional test
    let config = {
        num_tokens_aroundIdf: 3,
        num_tokens_around_point_of_interest: 5
    };

    // ------------------------------ Extract data given some specific nodes ------------
    try {
        // Extract data of every node apart from Identifier or Literal
        let dataFromSpecificNodes = new ExtractSingleLineChangedNodes(code, nonTrackingNodes, trackingNodes);

        let analysedCode = dataFromSpecificNodes.goThroughASTExtractSpecificNodes();
        for (let dt of analysedCode) {
            // For now, we do not need Identifier and the Context for the token sequence
            // dataFromSpecificNodes.addIdentifiersAndContext(dt, config);
            dataFromSpecificNodes.abstractIdentifiers(dt);
            dataFromSpecificNodes.abstractLiterals(dt);
        }

        let map_to_obj = (range_to_tok => {
            const obj = {};
            range_to_tok.forEach((v, k) => {
                obj[k] = v['value']
            });
            return obj;
        });
        return {
            'nodes': analysedCode,
            'functions_to_identifiers': dataFromSpecificNodes.scopeToIdentifier,
            'functions_to_literals': dataFromSpecificNodes.scopeToLiteral,
            'tokenList': dataFromSpecificNodes.tokenList.filter(value => value !== null),
            'tokenRangesList': dataFromSpecificNodes.tokenRangesList,
            'range_to_identifier': map_to_obj(dataFromSpecificNodes.rangeToIdentifier),
            'range_to_literal': map_to_obj(dataFromSpecificNodes.rangeToLiteral)
        };
    } catch (e) {
        return e;
    }

}

function extractNodeData(inFile, outFile) {
    // First format the file
    format_file(inFile);
    let code = '';
    try {
        code = fs.readFileSync(inFile, 'utf8');
    } catch (e) {
        return e;
    }

    let extractedData = analyseCode(code, ['Identifier', 'Literal'], ['BinaryExpression']);
    if (Object.keys(extractedData).length !== 0) {
        try {
            extractedData['file_path'] = inFile;
            // if (fs.existsSync(outFile)) {
            //     let knownLocationOfInterest = JSON.parse(fs.readFileSync(outFile, 'utf8'));
            //     if (knownLocationOfInterest && knownLocationOfInterest.hasOwnProperty('line')) {
            //         extractedData.line = knownLocationOfInterest.line;
            //     }
            // }
            if (fs.existsSync(outFile)) {
                let random_num = Math.floor(Math.random() * 100000);
                outFile = outFile.replace('.js', '_' + random_num + '.js')
            }
            fs.writeFileSync(outFile, JSON.stringify(extractedData));
        } catch (err) {
            return err;
        }

    }

    // console.log(outFile);
    // console.log(extractedData);
}


function parse_cli_arguments() {
    const ArgumentParser = require('argparse').ArgumentParser;
    let parser = new ArgumentParser({
        version: '0.0.1',
        addHelp: true,
        description: 'Go through the JS file and extract \'only\' certain the nodes'
    });

    // -------------------------- Debug ---------------------
    parser.addArgument(
        ['-inFile'],
        {help: 'Specify the source file from which the data needs to be extracted'});
    parser.addArgument(
        ['-outFile'],
        {help: 'Specify the file where the extracted data will be written'});
    let args = parser.parseArgs();
    return {
        'inFile': args.inFile,
        'outFile': args.outFile
    }
}


(
    async function () {
        let {
            inFile, outFile
        } = parse_cli_arguments();
        extractNodeData(inFile, outFile);
    }
)();

module.exports.analyseCode = analyseCode;
