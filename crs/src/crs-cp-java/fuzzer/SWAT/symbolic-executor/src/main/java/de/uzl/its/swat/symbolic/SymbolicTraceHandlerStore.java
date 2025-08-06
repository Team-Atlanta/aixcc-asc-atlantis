package de.uzl.its.swat.symbolic;
import de.uzl.its.swat.symbolic.trace.SymbolicTraceHandler;
import java.util.*;

public class SymbolicTraceHandlerStore {
  public static HashMap<Integer, Object[]> map;
  public static SymbolicTraceHandlerStore instance;

  public SymbolicTraceHandlerStore() {
    map = new HashMap<Integer, Object[]>();
  }

  public int getArgHashCode(Object[] args, Object[] types) {
    return args.hashCode() ^ types.hashCode();
  }

  public Object[] getTraceHandler(Object[] args, Object[] types) {
    int hashcode = getArgHashCode(args, types);
    Object[] ret = map.get(Integer.valueOf(hashcode));
    if (ret != null){
      System.out.println("getTraceHandler: " + ret.hashCode() + " for " + hashcode);
    }else{
      System.out.println("getTraceHandler: ret is null");
    }
    return ret;
  }

  public void setTraceHandler(Object[] args, Object[] types,
      SymbolicTraceHandler handler, int iid) {
    int hashcode = getArgHashCode(args, types);
    Object[] objectToStore = new Object[2];
    objectToStore[0] = handler;
    objectToStore[1] = Integer.valueOf(iid);
    if (objectToStore != null){
      System.out.println("setTraceHandler: " + objectToStore.hashCode() + " for " + hashcode);
    }else{
      System.out.println("setTraceHandler: objectToStore is null");
    }
    map.put(Integer.valueOf(hashcode), objectToStore);
  }

  public static SymbolicTraceHandlerStore getInstance() {
    if (instance == null) {
      instance = new SymbolicTraceHandlerStore();
    }
    return instance;
  }
}
