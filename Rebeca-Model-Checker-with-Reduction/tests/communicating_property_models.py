"""Supplied LoadBalancer and controlled property/queue/dependency mutations."""
import re
from pathlib import Path
from run_quiescence_models import ROOT
BOUNDS='property { Assertion { Balanced: Hub.PrimaryLoad >= 1 && Hub.PrimaryLoad <= 3 && Hub.SecondaryLoad >= 1 && Hub.SecondaryLoad <= 3; } }\n'
GLOBAL='property { Assertion { NoEarlyHub: !(Hub.SecondaryLoad == 2 && SecondarySrc.Cycle == 0); } }\n'
TRUE='property { Assertion { Trivial: true; } }\n'
def cases():
 source=(ROOT.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca').read_text()
 shared=source.replace('int SecondaryLoad;','').replace('SecondaryLoad','PrimaryLoad')
 fault=source.replace('Cycle = Cycle + 1;','Cycle = Cycle + 1; assertion(Cycle != 2);',1)
 # Remove the actual feedback in Hub only, leaving startup unchanged.
 hub=source.index('reactiveclass LoadBalancerHub');deadlock=source[:hub]+source[hub:].replace('PrimarySrc.Dispatch();','')
 conditional=source.replace('Relay.Forward();','if (Cycle == 1) { Relay.Forward(); }',1)
 renamed=source;renamed_prop=BOUNDS
 names={'SystemBootstrapper':'SeedActor','PrimarySource':'ProducerA','SecondarySource':'ProducerB','PrimaryRelay':'RelayA','SecondaryRelay':'RelayB','LoadBalancerHub':'Router','PrimarySrc':'Left','SecondarySrc':'Right','Bootstrapper':'Seed','Hub':'Center','Cycle':'Sequence','Round':'Pass','PrimaryLoad':'LeftCount','SecondaryLoad':'RightCount','Dispatch':'Push','Forward':'Relay','Initialize':'Boot','ReceivePrimary':'TakeLeft','ReceiveSecondary':'TakeRight'}
 for old,new in names.items():
  renamed=re.sub(r'\b'+old+r'\b',new,renamed);renamed_prop=re.sub(r'\b'+old+r'\b',new,renamed_prop)
 peer='reactiveclass Node(8) { knownrebecs { Node peer; } statevars { int value; } Node() { value=0; self.tick(); } msgsrv tick() { peer.tick(); peer.tick(); } } main { Node A(B):(); Node B(A):(); }\n'
 rw=source.replace('SecondaryLoad = SecondaryLoad + 1;','SecondaryLoad = PrimaryLoad;')
 three=rw.replace('PrimarySrc.Dispatch();','PrimarySrc.Dispatch(); PrimarySrc.Dispatch();',1)
 return [('load_bounds',source,BOUNDS,'satisfied',True),('load_true',source,TRUE,'satisfied',True),('renamed_load',renamed,renamed_prop,'satisfied',True),('shared_hub_field',shared,TRUE,'satisfied',True),('global_violation',source,GLOBAL,'assertion failed',True),('source_assertion',fault,BOUNDS,'assertion failed',True),('terminating',deadlock,BOUNDS,'deadlock',True),('conditional_send',conditional,BOUNDS,'deadlock',False),('queue_margin_refused',source.replace('(5)','(3)'),BOUNDS,'satisfied',False),('repeatable_fanout_overflow',peer,TRUE.replace('Trivial','Check'),'queue overflow',False),('read_write_hub',rw,TRUE,'satisfied',True),('three_token_union',three,TRUE,'satisfied',True)]
