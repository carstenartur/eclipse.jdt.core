/*******************************************************************************
 * Copyright (c) 2000, 2022 IBM Corporation and others.
 *
 * This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License 2.0
 * which accompanies this distribution, and is available at
 * https://www.eclipse.org/legal/epl-2.0/
 *
 * SPDX-License-Identifier: EPL-2.0
 *
 * Contributors:
 *     IBM Corporation - initial API and implementation
 *******************************************************************************/
package org.eclipse.jdt.internal.compiler.parser;

/**
 * IMPORTANT NOTE: These constants are dedicated to the internal Scanner implementation.
 * It is mirrored in org.eclipse.jdt.core.compiler public package where it is API.
 * The mirror implementation is using the backward compatible ITerminalSymbols constant
 * definitions (stable with 2.0), whereas the internal implementation uses TerminalTokens
 * which constant values reflect the latest parser generation state.
 */
/**
 * Maps each terminal symbol in the java-grammar into a unique integer.
 * This integer is used to represent the terminal when computing a parsing action.
 *
 * Disclaimer : These constant values are generated automatically using a Java
 * grammar, therefore their actual values are subject to change if new keywords
 * were added to the language (for instance, 'assert' is a keyword in 1.4).
 */
public interface TerminalTokens {

	// special tokens not part of grammar - not autogenerated
	int TokenNameNotAToken = 0,
							TokenNameWHITESPACE = 1000,
							TokenNameCOMMENT_LINE = 1001,
							TokenNameCOMMENT_BLOCK = 1002,
							TokenNameCOMMENT_JAVADOC = 1003,
							TokenNameSingleQuoteStringLiteral = 1004,
							TokenNameCOMMENT_MARKDOWN = 1005;

	static boolean isRestrictedKeyword(int tokenType) {
		return switch (tokenType) {
			case TokenNameRestrictedIdentifierYield, TokenNameRestrictedIdentifierrecord,TokenNameRestrictedIdentifierWhen,
					TokenNameRestrictedIdentifiersealed, TokenNameRestrictedIdentifierpermits -> true;
			default -> false;
		};
	}

	static int getRestrictedKeyword(char [] text) {
		if (text != null) {
			int len = text.length;
			if (len == 4 && text[0] == 'w' ||
				len == 5 && text[0] == 'y' ||
				len == 6 && (text[0] == 'r' || text[0] == 's') ||
				len == 7 && text[0] == 'p') {
				return getRestrictedKeyword(new String(text));
			}
		}
		return TokenNameNotAToken;
	}

	static int getRestrictedKeyword(String text) {
		return switch (text) {
			case "yield"   -> TokenNameRestrictedIdentifierYield;   //$NON-NLS-1$
			case "record"  -> TokenNameRestrictedIdentifierrecord;  //$NON-NLS-1$
			case "when"    -> TokenNameRestrictedIdentifierWhen;    //$NON-NLS-1$
			case "sealed"  -> TokenNameRestrictedIdentifiersealed;  //$NON-NLS-1$
			case "permits" -> TokenNameRestrictedIdentifierpermits; //$NON-NLS-1$
			default        -> TokenNameNotAToken;
		};
	}

	// BEGIN_AUTOGENERATED_REGION
	int TokenNameIdentifier = 19,
							TokenNameabstract = 44,
							TokenNameassert = 81,
							TokenNameboolean = 104,
							TokenNamebreak = 82,
							TokenNamebyte = 105,
							TokenNamecase = 106,
							TokenNamecatch = 107,
							TokenNamechar = 108,
							TokenNameclass = 71,
							TokenNamecontinue = 83,
							TokenNameconst = 136,
							TokenNamedefault = 77,
							TokenNamedo = 84,
							TokenNamedouble = 109,
							TokenNameelse = 121,
							TokenNameenum = 75,
							TokenNameextends = 92,
							TokenNamefalse = 54,
							TokenNamefinal = 45,
							TokenNamefinally = 117,
							TokenNamefloat = 110,
							TokenNamefor = 85,
							TokenNamegoto = 137,
							TokenNameif = 86,
							TokenNameimplements = 133,
							TokenNameimport = 111,
							TokenNameinstanceof = 17,
							TokenNameint = 112,
							TokenNameinterface = 72,
							TokenNamelong = 113,
							TokenNamenative = 46,
							TokenNamenew = 40,
							TokenNamenon_sealed = 47,
							TokenNamenull = 55,
							TokenNamepackage = 91,
							TokenNameprivate = 48,
							TokenNameprotected = 49,
							TokenNamepublic = 50,
							TokenNamereturn = 87,
							TokenNameshort = 114,
							TokenNamestatic = 38,
							TokenNamestrictfp = 51,
							TokenNamesuper = 36,
							TokenNameswitch = 65,
							TokenNamesynchronized = 41,
							TokenNamethis = 37,
							TokenNamethrow = 79,
							TokenNamethrows = 118,
							TokenNametransient = 52,
							TokenNametrue = 56,
							TokenNametry = 88,
							TokenNamevoid = 115,
							TokenNamevolatile = 53,
							TokenNamewhile = 80,
							TokenNamemodule = 116,
							TokenNameopen = 122,
							TokenNamerequires = 123,
							TokenNametransitive = 128,
							TokenNameexports = 124,
							TokenNameopens = 125,
							TokenNameto = 134,
							TokenNameuses = 126,
							TokenNameprovides = 127,
							TokenNamewith = 135,
							TokenNameIntegerLiteral = 57,
							TokenNameLongLiteral = 58,
							TokenNameFloatingPointLiteral = 59,
							TokenNameDoubleLiteral = 60,
							TokenNameCharacterLiteral = 61,
							TokenNameStringLiteral = 62,
							TokenNameTextBlock = 63,
							TokenNamePLUS_PLUS = 2,
							TokenNameMINUS_MINUS = 3,
							TokenNameEQUAL_EQUAL = 20,
							TokenNameLESS_EQUAL = 12,
							TokenNameGREATER_EQUAL = 13,
							TokenNameNOT_EQUAL = 21,
							TokenNameLEFT_SHIFT = 18,
							TokenNameRIGHT_SHIFT = 14,
							TokenNameUNSIGNED_RIGHT_SHIFT = 16,
							TokenNamePLUS_EQUAL = 93,
							TokenNameMINUS_EQUAL = 94,
							TokenNameMULTIPLY_EQUAL = 95,
							TokenNameDIVIDE_EQUAL = 96,
							TokenNameAND_EQUAL = 97,
							TokenNameOR_EQUAL = 98,
							TokenNameXOR_EQUAL = 99,
							TokenNameREMAINDER_EQUAL = 100,
							TokenNameLEFT_SHIFT_EQUAL = 101,
							TokenNameRIGHT_SHIFT_EQUAL = 102,
							TokenNameUNSIGNED_RIGHT_SHIFT_EQUAL = 103,
							TokenNameOR_OR = 31,
							TokenNameAND_AND = 30,
							TokenNamePLUS = 4,
							TokenNameMINUS = 5,
							TokenNameNOT = 67,
							TokenNameREMAINDER = 9,
							TokenNameXOR = 24,
							TokenNameAND = 22,
							TokenNameMULTIPLY = 8,
							TokenNameOR = 28,
							TokenNameTWIDDLE = 68,
							TokenNameDIVIDE = 10,
							TokenNameGREATER = 15,
							TokenNameLESS = 11,
							TokenNameLPAREN = 23,
							TokenNameRPAREN = 25,
							TokenNameLBRACE = 42,
							TokenNameRBRACE = 33,
							TokenNameLBRACKET = 6,
							TokenNameRBRACKET = 70,
							TokenNameSEMICOLON = 26,
							TokenNameQUESTION = 29,
							TokenNameCOLON = 66,
							TokenNameCOMMA = 32,
							TokenNameDOT = 1,
							TokenNameEQUAL = 78,
							TokenNameAT = 35,
							TokenNameELLIPSIS = 119,
							TokenNameARROW = 120,
							TokenNameCOLON_COLON = 7,
							TokenNameBeginLambda = 64,
							TokenNameBeginIntersectionCast = 69,
							TokenNameBeginTypeArguments = 89,
							TokenNameElidedSemicolonAndRightBrace = 73,
							TokenNameAT308 = 27,
							TokenNameAT308DOTDOTDOT = 129,
							TokenNameCaseArrow = 74,
							TokenNameRestrictedIdentifierYield = 90,
							TokenNameRestrictedIdentifierrecord = 76,
							TokenNameRestrictedIdentifiersealed = 43,
							TokenNameRestrictedIdentifierpermits = 130,
							TokenNameBeginCaseElement = 131,
							TokenNameRestrictedIdentifierWhen = 132,
							TokenNameUNDERSCORE = 34,
							TokenNameEOF = 39,
							TokenNameERROR = 138;
}
