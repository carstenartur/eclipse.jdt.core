/*******************************************************************************
 * Copyright (c) 2000, 2010 IBM Corporation and others.
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
package org.eclipse.jdt.internal.compiler.impl;

public class BooleanConstant extends Constant {

	public static final char[] TRUE_STRING = "TRUE".toCharArray(); //$NON-NLS-1$
	public static final char[] FALSE_STRING = "FALSE".toCharArray(); //$NON-NLS-1$

	private final boolean value;

	private static final BooleanConstant TRUE = new BooleanConstant(true);
	private static final BooleanConstant FALSE = new BooleanConstant(false);

	public static Constant fromValue(boolean value) {
		return value ? BooleanConstant.TRUE : BooleanConstant.FALSE;
	}

	private BooleanConstant(boolean value) {
		this.value = value;
	}

	@Override
	public boolean booleanValue() {
		return this.value;
	}

	@Override
	public int intValue() {
		return this.value ? 1 : 0;
	}

	@Override
	public String stringValue() {
		// spec 15.17.11
		return String.valueOf(this.value);
	}

	@Override
	public String toString() {
		return "(boolean)" + this.value; //$NON-NLS-1$
	}

	@Override
	public int typeID() {
		return T_boolean;
	}

	@Override
	public int hashCode() {
		return this.value ? 1231 : 1237;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj) {
			return true;
		}
		if (obj == null) {
			return false;
		}
		if (getClass() != obj.getClass()) {
			return false;
		}
		// cannot be true anymore as the first test would have returned true
		return false;
	}
}
