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

package qilin.pta.toolkits.common;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import qilin.core.PTA;
import qilin.core.builder.MethodNodeFactory;
import qilin.core.pag.PAG;
import qilin.core.pag.VarNode;
import sootup.core.model.SootMethod;
import sootup.core.types.ReferenceType;

public class ToolUtil {
  public static VarNode getThis(PAG pag, SootMethod m) {
    MethodNodeFactory mthdNF = pag.getMethodPAG(m).nodeFactory();
    return mthdNF.caseThis();
  }

  public static Set<VarNode> getParameters(PAG pag, SootMethod m) {
    MethodNodeFactory mthdNF = pag.getMethodPAG(m).nodeFactory();
    Set<qilin.core.pag.VarNode> ret = new HashSet<>();
    for (int i = 0; i < m.getParameterCount(); ++i) {
      if (m.getParameterType(i) instanceof ReferenceType) {
        qilin.core.pag.VarNode param = mthdNF.caseParm(i);
        ret.add(param);
      }
    }
    return ret;
  }

  public static Set<VarNode> getRetVars(PAG pag, SootMethod m) {
    MethodNodeFactory mthdNF = pag.getMethodPAG(m).nodeFactory();
    if (m.getReturnType() instanceof ReferenceType) {
      VarNode ret = mthdNF.caseRet();
      return Collections.singleton(ret);
    }
    return Collections.emptySet();
  }

  public static int pointsToSetSizeOf(final PTA pta, VarNode var) {
    return pta.reachingObjects(var).toCIPointsToSet().size();
  }
}
