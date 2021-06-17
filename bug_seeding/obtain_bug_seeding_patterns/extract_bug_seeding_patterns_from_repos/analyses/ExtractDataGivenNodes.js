/**
 Extract data for some given Node types in Code.
 **/
const CodeAnalysis = require('../CodeAnalysis').CodeAnalysis;
const estraverse = require('estraverse');

class ExtractSingleLineChangedNodes extends CodeAnalysis {
    constructor(code, nonTrackingNodes) {
        super(code);
        this.nonTrackingNodes = nonTrackingNodes;
    }

    goThroughASTExtractSpecificNodes() {
        let extracted_data = [];

        let functionNameStack = new Map();
        let self = this; // Since this is not callable form the call back. We assign it to a variable

        if (Object.keys(this.ast).length < 1)
            return extracted_data;
        estraverse.traverse(this.ast, {
            enter: function (node, parent) {

                let range = node.range[0] + '-' + node.range[1];
                let line = node.loc.start.line + '-' + node.loc.end.line;
                // if (matchStatement.test(node.type))
                //     parents.push(node);
                if (node.type === 'Program') {
                    // Anything declared in the global scope is considered to be in the __GLOBAL function
                    let functionName_loc = '__GLOBAL' + '_' + range;
                    functionNameStack.set(functionName_loc, range);
                    return;
                }

                if (node.type === 'FunctionExpression' || node.type === 'FunctionDeclaration') {
                    // Name of the function or Anonymous function
                    let functionName = node.id !== null ? node.id.name : '__ANONYMOUS__';
                    let functionName_loc = functionName + '_' + range;
                    functionNameStack.set(functionName_loc, range);
                    return;
                }

                // Ignore any node that spans more than one line
                if (node.loc.start.line !== node.loc.end.line) return;


                let belongingFunction = Array.from(functionNameStack.keys())[functionNameStack.size - 1];

                if (!self.nonTrackingNodes.includes(node.type)) { // Ignore Identifiers and Literals
                    try {


                        let [start_index, end_index] = self.findTokenIndexFromRange(node.range[0], node.range[1]);
                        let tokenTypes = self.tokenTypesList.slice(start_index, end_index);
                        // let tokenRanges = self.tokenRangesList.slice(start_index, end_index);
                        let tokens = self.tokenList.slice(start_index, end_index);
                        // let p = parents[parents.length - 1];

                        extracted_data.push({
                            tokens: tokens,
                            tokenTypes: tokenTypes,
                            // tokenRanges: tokenRanges,
                            range: node.range,
                            type: node.type,
                            line: line,
                            belongs_to_function: belongingFunction,
                            belonging_function_range: functionNameStack.get(belongingFunction),
                            // parent: p.type,
                            // parent_line: p.loc.start.line + '-' + p.loc.end.line,
                            // parent_range: p.range
                        });
                    } catch (e) {
                        console.log(`Node ${node.type} could not be analysed properly`);
                        // console.log(e);
                    }
                }
            },

            leave: function (node, parent) {
                if (node.type === 'FunctionExpression' || node.type === 'FunctionDeclaration') {
                    let lastFunctionName = Array.from(functionNameStack.keys())[functionNameStack.size - 1];
                    functionNameStack.delete(lastFunctionName);
                }
            }
        });
        return extracted_data;
    }

    /**
     * Given extracted data, add the Identifier context and context of the test tokens.
     *
     * @param {Object} extracted_data
     * @param {Object} numOfTokens - Context size as 'numOfTokens'
     */
    addIdentifiersAndContext(extracted_data, numOfTokens) {
        // How many tokens to extract around each Identifier context and also around the test tokens of the conditional
        let {
            num_tokens_aroundIdf,
            num_tokens_around_point_of_interest
        } = numOfTokens;

        let functionStartRange = extracted_data.belonging_function_range.split('-')[0],
            functionEndRange = extracted_data.belonging_function_range.split('-')[1];

        // All indices correspond to tokenRangeList, tokenTypeList and tokenList
        let [start_index_function, end_index_function] = this.findTokenIndexFromRange(functionStartRange, functionEndRange);
        let [start_index, end_index] = this.findTokenIndexFromRange(extracted_data.range[0], extracted_data.range[1]);

        let rangesOfTestTokens = this.tokenRangesList.slice(start_index, end_index);

        // The start of the function, the conditional belongs to
        let startContextIndex = start_index_function;
        // The range of the previous context starts from the start of the function until the start of the test of the conditional.
        let pre_rangeLimit = [functionStartRange, extracted_data.range[0]];

        // The end of the function
        let endContextIndex = end_index_function;

        // The range of the later context starts from the end of the conditional until the end of the conditional body range
        let later_rangeLimit = [extracted_data.range[1], functionEndRange];

        let rangesOfIdfs = this.extractContextOfIdentifiersInPointOfInterest(rangesOfTestTokens, pre_rangeLimit, later_rangeLimit, extracted_data.belonging_function_range);

        // Find the index of the start and end from where context will be extracted

        let identifiersInTokenList = [];
        for (let idf of rangesOfIdfs) {

            let idfAndContext = {
                value: idf.value,
                // line: idf.line,
                prev_usages: [],
                later_usages: []
            };

            // Extract tokens around the previous usages of the Identifier
            for (let idr of idf.previous_ranges) {
                let idfIdx = this.tokenRangesList.indexOf(idr.idfRange);
                let tokensAroundIdf = this.extractTokensAroundPointOfInterest(startContextIndex, endContextIndex, idfIdx, idfIdx, num_tokens_aroundIdf);
                idfAndContext.prev_usages.push(tokensAroundIdf);
                // idfAndContext.prev_usages.push(tokensAroundIdf.tokensBeforPoi.concat(idf.value).concat(tokensAroundIdf.tokensAfterPoi));
            }

            // Extract tokens around the later usages of the Identifier
            for (let idr of idf.later_ranges) {
                let idfIdx = this.tokenRangesList.indexOf(idr.idfRange);
                let tokensAroundIdf = this.extractTokensAroundPointOfInterest(startContextIndex, endContextIndex, idfIdx, idfIdx, num_tokens_aroundIdf);
                idfAndContext.later_usages.push(tokensAroundIdf)
                // idfAndContext.later_usages.push(tokensAround;Idf.tokensBeforPoi.concat(idf.value).concat(tokensAroundIdf.tokensAfterPoi));
            }

            identifiersInTokenList.push(idfAndContext);
        }

        // let identifiersInScope = this.scopeToIdentifier.get(conditional.belonging_function_range);

        extracted_data.identifiers = identifiersInTokenList;
        // extracted_data.tokensAroundConditional = tokensAroundConditional;
        // return [identifiersInTest, tokensAroundConditional];

    }

    /**
     * Given a conditional, abstract away all Identifiers
     * @param {Object} extracted_data
     */
    abstractIdentifiers(extracted_data) {
        let idfValToId = new Map();
        let count = 1;
        let abstractedTokens = [],
            sourceTokens = [];

        if (extracted_data.hasOwnProperty('abstractedTokens')) {
            abstractedTokens = extracted_data.abstractedTokens;
            sourceTokens = extracted_data.abstractedTokens;
        } else {
            while (abstractedTokens.length != extracted_data.tokenTypes.length) {
                abstractedTokens.push(null);
            }
            sourceTokens = extracted_data.tokens;
        }

        for (let t = 0; t < extracted_data.tokenTypes.length; t++) {
            if (extracted_data.tokenTypes[t] === 'Identifier') {
                let idfVal = extracted_data.tokens[t];
                if (idfVal) {
                    let id = idfValToId.get(idfVal) || 'Idf_' + count++;
                    idfValToId.set(idfVal, id);
                    abstractedTokens[t] = id;
                }
            } else {
                abstractedTokens[t] = sourceTokens[t];
            }
        }
        extracted_data.abstractedTokens = abstractedTokens;
    }


    /**
     * Given a conditional, abstract away all Literals
     * @param {Object} extracted_data
     */
    abstractLiterals(extracted_data) {
        let litValToId = new Map();
        let count = 1;
        let abstractedTokens = [],
            sourceTokens = [];

        if (extracted_data.hasOwnProperty('abstractedTokens')) {
            abstractedTokens = extracted_data.abstractedTokens;
            sourceTokens = extracted_data.abstractedTokens;
        } else {
            while (abstractedTokens.length != extracted_data.tokenTypes.length) {
                abstractedTokens.push(null);
            }
            sourceTokens = extracted_data.tokens;
        }

        for (let t = 0; t < extracted_data.tokenTypes.length; t++) {
            if (extracted_data.tokenTypes[t] === 'Literal') {
                let litVal = extracted_data.tokens[t];
                if (litVal) {
                    let id = litValToId.get(litVal) || 'Lit_' + count++;
                    litValToId.set(litVal, id);
                    abstractedTokens[t] = id;
                }
            } else {
                abstractedTokens[t] = sourceTokens[t];
            }
        }
        extracted_data.abstractedTokens = abstractedTokens;
    }
}

module.exports.ExtractSingleLineChangedNodes = ExtractSingleLineChangedNodes;