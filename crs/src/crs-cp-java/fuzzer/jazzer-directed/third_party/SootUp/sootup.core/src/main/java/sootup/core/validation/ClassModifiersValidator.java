package sootup.core.validation;

/*-
 * #%L
 * Soot - a J*va Optimization Framework
 * %%
 * Copyright (C) 1997-2020 Raja Vallée-Rai, Linghui Luo, Akshita Dubey
 * %%
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 2.1 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Lesser Public License for more details.
 *
 * You should have received a copy of the GNU General Lesser Public
 * License along with this program.  If not, see
 * <http://www.gnu.org/licenses/lgpl-2.1.html>.
 * #L%
 */

import java.util.List;
import sootup.core.model.SootClass;

/**
 * Validator that checks for impossible combinations of class modifiers
 *
 * @author Steven Arzt
 */
public class ClassModifiersValidator implements ClassValidator {

  @Override
  public void validate(SootClass sc, List<ValidationException> exceptions) {

    if (sc.isInterface()) {
      if (sc.isEnum()) {
        exceptions.add(new ValidationException(sc, "Class is both an interface and an enum"));
      }
      if (sc.isSuper()) {
        exceptions.add(new ValidationException(sc, "Class is both an interface and a super class"));
      }
      if (sc.isFinal()) {
        exceptions.add(new ValidationException(sc, "Class is both an interface and final"));
      }
      if (!sc.isAbstract()) {
        exceptions.add(
            new ValidationException(sc, "Class must be both an interface and an abstract class"));
      }
    }
    if (sc.isAnnotation()) {
      if (!sc.isInterface()) {
        exceptions.add(
            new ValidationException(sc, "Class must be both an annotation and an interface"));
      }
    }
  }

  @Override
  public boolean isBasicValidator() {
    return true;
  }
}
