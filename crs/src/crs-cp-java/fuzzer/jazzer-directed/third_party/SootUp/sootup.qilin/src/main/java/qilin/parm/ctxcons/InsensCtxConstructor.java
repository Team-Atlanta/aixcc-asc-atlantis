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

package qilin.parm.ctxcons;

import qilin.core.context.Context;
import qilin.core.pag.CallSite;
import qilin.core.pag.ContextAllocNode;
import qilin.core.pag.ContextMethod;
import sootup.core.model.SootMethod;

public class InsensCtxConstructor implements CtxConstructor {

  @Override
  public Context constructCtx(
      ContextMethod caller, ContextAllocNode receiverNode, CallSite callSite, SootMethod target) {
    return emptyContext;
  }
}
