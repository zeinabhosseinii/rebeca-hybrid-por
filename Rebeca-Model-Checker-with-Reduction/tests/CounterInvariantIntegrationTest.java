import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import com.google.gson.*;
import org.rebecalang.compiler.CompilerConfig;
import org.rebecalang.compiler.modelcompiler.RebecaModelCompiler;
import org.rebecalang.compiler.modelcompiler.corerebeca.objectmodel.RebecaModel;
import org.rebecalang.compiler.utils.*;
import org.rebecalang.rmc.*;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/** Compare production certificate to all mutation expectations; check per-call isolation. */
public class CounterInvariantIntegrationTest {
 public static void main(String[] args)throws Exception{
  var summary=JsonParser.parseString(Files.readString(Path.of(args[0],"summary.json"))).getAsJsonObject();
  Map<String,RebecaModel> models=new LinkedHashMap<>();Map<String,Boolean> expected=new LinkedHashMap<>();
  try(var context=new AnnotationConfigApplicationContext(CompilerConfig.class,RMCConfig.class)){
   var compiler=context.getBean(RebecaModelCompiler.class);var errors=context.getBean(ExceptionContainer.class);
   for(var entry:summary.getAsJsonObject("cases").entrySet()){
    errors.clear();String name=entry.getKey();var pair=compiler.compileRebecaFile(Path.of(args[0],name,name+".rebeca").toFile(),Set.of(CompilerExtension.TIMED_REBECA),CoreVersion.CORE_2_3);
    if(!errors.exceptionsIsEmpty())throw new AssertionError("source compile failed: "+name);
    boolean want=entry.getValue().getAsJsonObject().get("expected_certificate").getAsBoolean();RebecaModel model=pair.getFirst();models.put(name,model);expected.put(name,want);
    if(CounterInvariantCertificate.provesAllAssertions(model)!=want || ERDGSafetyAnalyzer.supportsFullExpansionBarriers(model)!=want)throw new AssertionError("gate/certificate mismatch: "+name);
   }
   var workers=Executors.newFixedThreadPool(4);
   try{
    List<Callable<Boolean>> tasks=new ArrayList<>();
    for(int repeat=0;repeat<8;repeat++)for(String name:models.keySet())tasks.add(()->CounterInvariantCertificate.provesAllAssertions(models.get(name))==expected.get(name));
    for(var result:workers.invokeAll(tasks))if(!result.get())throw new AssertionError("shared-state leakage");
   }finally{workers.shutdownNow();}
  }
  System.out.println("PASS: "+models.size()+" production mutation gates and 136 concurrent certificate calls");
 }
}
