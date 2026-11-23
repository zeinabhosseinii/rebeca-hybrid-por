import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import org.rebecalang.compiler.CompilerConfig;
import org.rebecalang.compiler.modelcompiler.RebecaModelCompiler;
import org.rebecalang.compiler.propertycompiler.PropertyCompiler;
import org.rebecalang.compiler.utils.*;
import org.rebecalang.rmc.*;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

public class PropertyMetadataPolicyTest {
 static void require(boolean ok,String why){if(!ok)throw new AssertionError(why);}
 static boolean empty(List<List<Boolean>> table){return table.stream().flatMap(Collection::stream).noneMatch(Boolean::booleanValue);}
 public static void main(String[] args)throws Exception{
  try(var context=new AnnotationConfigApplicationContext(CompilerConfig.class,RMCConfig.class)){
   var errors=context.getBean(ExceptionContainer.class);errors.clear();var model=context.getBean(RebecaModelCompiler.class).compileRebecaFile(Path.of(args[0]).toFile(),Set.of(CompilerExtension.TIMED_REBECA),CoreVersion.CORE_2_3).getFirst();
   var property=context.getBean(PropertyCompiler.class).compilePropertyFile(Path.of(args[1]).toFile(),model,Set.of(CompilerExtension.TIMED_REBECA));require(errors.exceptionsIsEmpty(),"compiler errors");
   var expected=PropertyObservationMetadata.invisibleTable(model,property,2,true);
   require(expected.size()==4 && !expected.get(0).get(1) && expected.get(0).get(2) && expected.get(1).get(1) && !expected.get(2).get(1) && expected.get(3).get(1),"wrong actor/message identity or visibility");
   require(empty(PropertyObservationMetadata.invisibleTable(model,property,2,false)),"disabled permits partial choices");
   require(empty(PropertyObservationMetadata.invisibleTable(model,null,2,true)),"missing property permits partial choices");
   require(empty(PropertyObservationMetadata.invisibleTable(model,property,1,true)),"truncated ID space permits partial choices");
   var pool=Executors.newFixedThreadPool(4);
   try{
    List<Callable<Boolean>> jobs=new ArrayList<>();
    for(int n=0;n<32;n++){final boolean enable=n%2==0;jobs.add(()->{var actual=PropertyObservationMetadata.invisibleTable(model,property,2,enable);return enable?actual.equals(expected):empty(actual);});}
    for(var future:pool.invokeAll(jobs))require(future.get(),"concurrent metadata leaked permissions");
   }finally{pool.shutdownNow();}
   var mutated=PropertyObservationMetadata.invisibleTable(model,property,2,true);mutated.get(0).set(1,true);require(!PropertyObservationMetadata.invisibleTable(model,property,2,true).get(0).get(1),"caller mutation leaked to later tables");
   System.out.println("PASS: production IDs, refusal/truncation, 32 concurrent calls and isolated tables");
  }
 }
}
