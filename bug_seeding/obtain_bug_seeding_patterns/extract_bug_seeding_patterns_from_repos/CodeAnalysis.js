/**
 * The super class of all code analysis.
 * Each analysis extends this
 */
const assert = require('assert');

const esprima = require('esprima'),
    estraverse = require('estraverse'),
    beautify = require('js-beautify').js,
    strip = require('strip-comments'),
    escodegen = require('escodegen');

class CodeAnalysis {
    constructor(code) {
        let {ast, rangeToNodeType, rangeToIdentifier, IdentifierToRange, rangeToLiteral, LiteralToRange} = CodeAnalysis.getASTData(code);
        let {tokenList, tokenRangeList, tokenTypeList, lineToTokenSequence} = CodeAnalysis.getTokenData(ast, rangeToNodeType, rangeToLiteral);
        if (ast.hasOwnProperty('tokens'))
            assert.ok(tokenList.length === ast.tokens.length);
        this.ast = ast;

        // Mapping between node's range to different things
        this.rangeToASTNodeType = rangeToNodeType;
        this.rangeToIdentifier = rangeToIdentifier;
        this.IdentifierToRange = IdentifierToRange;
        this.LiteralToRange = LiteralToRange;

        // A mapping between range of a 'function' and all Identifiers in it
        this.scopeToIdentifier = CodeAnalysis.mapScopeToIdentifier(IdentifierToRange);
        this.scopeToLiteral = CodeAnalysis.mapScopeToLiteral(LiteralToRange);


        this.rangeToLiteral = rangeToLiteral;

        this.tokenList = tokenList;
        this.tokenRangesList = tokenRangeList;
        this.tokenTypesList = tokenTypeList;
        this.lineToTokenSequence = lineToTokenSequence; // The corresponding token sequence for each line
    }

    /**
     *
     * Given ast, tokenize it using esprima
     * @param {Object} ast
     * @param {Map} rangeToASTNodeType
     * @param {Map} rangeToLiteral
     * @returns {Object}
     *
     * */
    static getTokenData(ast, rangeToASTNodeType, rangeToLiteral) {
        let tokens = ast.hasOwnProperty('tokens') ? ast.tokens : [];
        /*let config = {
            range: true,
            loc: true
        };*/

        /* try {
             // Not using the tokenizer since esprima tokenizer could have bugs https://github.com/jquery/esprima/issues/2001
             tokens = esprima.tokenize(ast, config);
         } catch (error) {
             console.log(error);
             tokens = [];
         }*/

        let tokenList = [];
        let tokenRangeList = [];
        let tokenTypeList = [];
        let lineToTokenSequence = {};

        for (let token of tokens) {
            let tokenStartLine = token.loc.start.line, tokenEndLine = token.loc.end.line;
            let curTokenRange = token.range[0] + "-" + token.range[1];
            let tokenVal = null;

            if (rangeToLiteral.has(curTokenRange))
                tokenVal = rangeToLiteral.get(curTokenRange).value;
            else
                tokenVal = token.value;

            tokenList.push(tokenVal);
            tokenTypeList.push(token.type);

            tokenRangeList.push(curTokenRange);

            if (tokenStartLine === tokenEndLine) { // We are only interested in tokens that start and end in the same line
                if (!lineToTokenSequence.hasOwnProperty(tokenStartLine)) {
                    lineToTokenSequence[tokenStartLine] = [];
                }
                lineToTokenSequence[tokenStartLine].push(tokenVal);
            }
        }
        assert.ok(tokenList.length === tokenRangeList.length, 'TokenList and TokenRangeList should have same size');
        assert.ok(tokenList.length === tokenTypeList.length, 'Both tokenList and tokenTypeList should have same size');

        CodeAnalysis.fixTokenTypeList(tokenTypeList, tokenRangeList, rangeToASTNodeType);
        return {tokenList, tokenRangeList, tokenTypeList, lineToTokenSequence};
    }

    /*
         As pointed out by https://github.com/jquery/esprima/blob/master/docs/lexical-analysis.md#limitation-on-keywords,
         the token type list may mislabel some Identifiers as 'Keyword'. In addition, the token type list also
         does not contain 'Literals'. We use ASTNodeRanges to fix this.
         First, populate the K_tokensType_left and K_tokensType_right using the tokenTypeList and then
         fix the mislabels
    */
    static fixTokenTypeList(tokeTypeList, tokenTypeRangeList, rangeToASTNodeType) {
        for (let i = 0; i < tokenTypeRangeList.length; i++) {
            let range = tokenTypeRangeList[i];
            if (rangeToASTNodeType.has(range)) {
                tokeTypeList[i] = rangeToASTNodeType.get(range);
            }
        }
    }

    /**
     * Map a Literal to the Function it belongs to
     *
     */
    static mapScopeToLiteral(literalToRange) {
        let scopeToLit = {};
        literalToRange.forEach((value, key) => {
            value.forEach(lit_info => {
                let scope = lit_info.belonging_function_range;
                if (!scopeToLit.hasOwnProperty(scope)) {
                    scopeToLit[scope] = [];
                }
                if (!scopeToLit[scope].includes(key))
                    scopeToLit[scope].push(key);
                // let lits = scopeToLit.get(scope) || new Set();
                // lits.add(key);
                // scopeToLit.set(scope, lits);
            });
        });
        return scopeToLit;
    }

    /**
     * Map an Identifier to the Functin it belongs to
     * @param identifierToRange{Map<Array<Object<String,String>>>}
     */
    static mapScopeToIdentifier(identifierToRange) {
        let scopeToIdf = {};
        identifierToRange.forEach((value, key) => {
            value.forEach(idf_info => {
                let scope = idf_info.belonging_function_range;
                if (!scopeToIdf.hasOwnProperty(scope)) {
                    scopeToIdf[scope] = [];
                }
                if (!scopeToIdf[scope].includes(key))
                    scopeToIdf[scope].push(key);
                // let idfs = scopeToIdf.get(scope) || new Set();
                // idfs.add(key);
                // scopeToIdf.set(scope, idfs);
            });
        });
        return scopeToIdf;
    }


    /**
     *
     * @param {string} code
     * @returns {Object}
     */
    static getASTData(code) {
        let ast = {},
            rangeToNodeType = new Map(), astNodeTypeList = [],
            rangeToIdentifier = new Map(), IdentifierToRange = new Map(), rangeToLiteral = new Map(),
            LiteralToRange = new Map();
        let config = {
            range: true,
            loc: true,
            tokens: true
        };
        let functionNameStack = new Map();

        try {
            /**
             * Unfortunately, we can't prettify the code here. The reason being, we use the original line
             * number from code to match the nodes to changes made in commit
             *  */
            ast = esprima.parseScript(code, config);
        } catch (error) {
            // console.error(error);

            ast = {};
            // console.error(`Can't parse code ${code} `);
            // console.log(`Can't parse code`);
        }

        // ------ Traverse and gather some info
        try {
            // Once, we have the ast, we 
            estraverse.traverse(ast, {
                enter: function (node, parent) {
                    let range = node.range[0] + "-" + node.range[1];
                    let line = node.loc.start.line + '-' + node.loc.end.line;
                    rangeToNodeType.set(range, node.type);
                    astNodeTypeList.push(node.type);

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

                    let belongingFunction = Array.from(functionNameStack.keys())[functionNameStack.size - 1];

                    if (node.type === 'Identifier') {
                        rangeToIdentifier.set(range, {value: node.name, line: line});
                        let idfranges = IdentifierToRange.get(node.name) || [];
                        idfranges.push({
                            idfRange: range,
                            belonging_function_range: functionNameStack.get(belongingFunction)
                        });

                        IdentifierToRange.set(node.name, idfranges);
                    } else if (node.type === 'Literal') {
                        let litVal = node.raw;

                        /* if (node.value === null)
                             litVal = String(node.value);
                         else
                             litVal = node.value;*/

                        let litranges = LiteralToRange.get(litVal) || [];
                        litranges.push({
                            litRange: range,
                            belonging_function_range: functionNameStack.get(belongingFunction)
                        });
                        LiteralToRange.set(litVal, litranges);
                        rangeToLiteral.set(range, {value: litVal, line: line});
                    }
                },
                leave: function (node, parent) {
                    if (node.type === 'FunctionExpression' || node.type === 'FunctionDeclaration') {
                        let lastFunctionName = Array.from(functionNameStack.keys())[functionNameStack.size - 1];
                        functionNameStack.delete(lastFunctionName);
                    }
                }
            });
        } catch (error) {
            ast = {};
            rangeToNodeType = new Map();
            astNodeTypeList = [];
            rangeToIdentifier = new Map();
            IdentifierToRange = new Map();
            rangeToLiteral = new Map();
            LiteralToRange = new Map();
            // console.log("Can't traverse AST");
        }

        return {
            ast,
            rangeToNodeType,
            astNodeTypeList,
            rangeToIdentifier,
            IdentifierToRange,
            rangeToLiteral,
            LiteralToRange
        };
    }

    /**
     * Given ranges of tokens, find the index of the token in the tokenList
     * @param {Number} start_loc
     * @param {Number} end_loc
     */
    findTokenIndexFromRange(start_loc, end_loc) {

        // Checks only if the start matches the pattern
        let start_pattern = new RegExp('^' + start_loc + '-');
        // Checks only if the end matches the pattern
        let end_pattern = new RegExp('-' + end_loc + '$');

        let start_index = this.tokenRangesList.findIndex((elem) => start_pattern.test(elem));
        let end_index = this.tokenRangesList.findIndex((elem) => end_pattern.test(elem)) + 1;

        return [start_index, end_index]
    }

    /**
     *
     * @param contextStartIdx
     * @param contextEndIdx
     * @param poiStartIdx
     * @param poiEndIdx
     * @param numOfTokensToExtract
     * @returns {{tokensAfter: Array, tokensBefore: Array}}
     */
    extractTokensAroundPointOfInterest(contextStartIdx, contextEndIdx, poiStartIdx, poiEndIdx, numOfTokensToExtract) {

        // console.log("Number of tokens to extract ", numOfTokensToExtract);
        let tokStartIdx = poiStartIdx - numOfTokensToExtract, tokEndIdx = poiEndIdx + numOfTokensToExtract + 1;

        tokStartIdx = tokStartIdx < contextStartIdx ? contextStartIdx : tokStartIdx;
        tokEndIdx = tokEndIdx > contextEndIdx ? contextEndIdx : tokEndIdx;

        return {
            tokensBefore: this.tokenList.slice(tokStartIdx, poiStartIdx),
            tokensAfter: this.tokenList.slice(poiEndIdx + 1, tokEndIdx)
        };
    }

    /**
     * Given token ranges of a point of interest (Eg. Conditional 'test', Assignment)
     * find the Identifiers and then for each Identifier
     * get the context (all usage of the identifier in the code).
     * @param {Array} rangesOfTokens
     * @param {Array} pre_rangeLimit
     * @param {Array} later_rangeLimit
     * @param {Array} currentFunctionRange
     */
    extractContextOfIdentifiersInPointOfInterest(rangesOfTokens, pre_rangeLimit, later_rangeLimit, currentFunctionRange) {
        let idfRanges = [], rangeToIdentifier = this.rangeToIdentifier, identifierToRange = this.IdentifierToRange;

        for (let range of rangesOfTokens) {
            if (rangeToIdentifier.has(range)) { // Means it is an identifier
                let idfValue = rangeToIdentifier.get(range).value;
                let curIdfRanges = identifierToRange.get(idfValue);
                idfRanges.push(
                    {
                        value: idfValue,
                        line: rangeToIdentifier.get(range).line,
                        previous_ranges: curIdfRanges.filter(rng => rng.belonging_function_range === currentFunctionRange && range !== rng.idfRange && parseInt(rng.idfRange.split('-')[0]) >= pre_rangeLimit[0] && parseInt(rng.idfRange.split('-')[1]) <= pre_rangeLimit[1]),
                        later_ranges: curIdfRanges.filter(rng => rng.belonging_function_range === currentFunctionRange && range !== rng.idfRange && parseInt(rng.idfRange.split('-')[0]) >= later_rangeLimit[0] && parseInt(rng.idfRange.split('-')[1]) <= later_rangeLimit[1])
                    }
                );

            }
        }
        return idfRanges;
    }
}

module.exports.CodeAnalysis = CodeAnalysis;