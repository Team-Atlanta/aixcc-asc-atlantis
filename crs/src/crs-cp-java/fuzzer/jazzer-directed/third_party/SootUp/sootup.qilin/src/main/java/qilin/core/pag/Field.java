/* Qilin - a Java Pointer Analysis Framework
 * Copyright (C) 2021-2030 Qilin developers
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 3.0 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Lesser Public License for more details.
 *
 * You should have received a copy of the GNU General Lesser Public
 * License along with this program.  If not, see
 * <https://www.gnu.org/licenses/lgpl-3.0.en.html>.
 */

package qilin.core.pag;

import java.util.Objects;
import sootup.core.model.SootField;
import sootup.core.types.Type;

/** a wrapper of normal field. */
public class Field implements SparkField {
  private final SootField field;

  public Field(SootField sf) {
    this.field = sf;
  }

  @Override
  public Type getType() {
    return field.getType();
  }

  public SootField getField() {
    return field;
  }

  @Override
  public String toString() {
    return "FieldNode " + field;
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    Field field1 = (Field) o;
    return field.equals(field1.field);
  }

  @Override
  public int hashCode() {
    return Objects.hash(field);
  }
}
