"""Communicating workload with parameters actually consumed in scalar updates/guards."""
from communicating_property_models import cases as base_cases,BOUNDS,GLOBAL,TRUE

def parameterized(limit):
 source=base_cases()[0][1]
 for method in ('Dispatch','Forward','ReceivePrimary','ReceiveSecondary'):
  source=source.replace(method+'()',method+'(int limit)')
  source=source.replace('.'+method+'(int limit)','. '+method+'('+str(limit)+')').replace('. '+method,'.'+method)
 source=source.replace('Cycle > 2','Cycle > limit').replace('Round > 2','Round > limit')
 source=source.replace('PrimaryLoad > 3','PrimaryLoad > limit + 1').replace('SecondaryLoad > 3','SecondaryLoad > limit + 1')
 # The bound parameter affects every runtime actor's branch, not only metadata.
 return source,BOUNDS.replace('<= 3','<= '+str(limit+1))

def cases():
 result=[]
 for limit in (2,5,11,47,191):
  source,prop=parameterized(limit)
  result.append(('load_period_'+str(limit+1),source,prop,'satisfied',True))
 source,prop=parameterized(2)
 result.append(('fixed_parameter_global_error',source,GLOBAL,'assertion failed',True))
 fault=source.replace('Cycle = Cycle + 1;','Cycle = Cycle + 1; assertion(Cycle != limit);',1)
 result.append(('fixed_parameter_source_error',fault,prop,'assertion failed',True))
 start=source.index('reactiveclass LoadBalancerHub')
 deadlock=source[:start]+source[start:].replace('PrimarySrc.Dispatch(2);','')
 result.append(('fixed_parameter_deadlock',deadlock,prop,'deadlock',True))
 shared=base_cases()[3][1]
 for method,value in [('ReceivePrimary',1),('ReceiveSecondary',2)]:
  shared=shared.replace(method+'()',method+'(int increment)').replace('.'+method+'(int increment)','.'+method+'('+str(value)+')')
 shared=shared.replace('PrimaryLoad = PrimaryLoad + 1;','PrimaryLoad = PrimaryLoad + increment;')
 result.append(('different_constants_same_syntax',shared,TRUE,'satisfied',True))
 mixed=source.replace('PrimarySrc.Dispatch(2);','PrimarySrc.Dispatch(3);',1)
 result.append(('mixed_used_payloads',mixed,prop,'satisfied',True))

 # Both values can be simultaneously enabled at a single receiver and handler.
 mixed=mixed.replace('PrimarySrc.Dispatch(3);','PrimarySrc.Dispatch(7); PrimarySrc.Dispatch(9);',1)
 result.append(('three_token_mixed_payloads',mixed,TRUE,'satisfied',True))
 fault=mixed.replace('Cycle = Cycle + 1;','assertion(limit != 9); Cycle = Cycle + 1;',1)
 result.append(('three_token_payload_assertion',fault,TRUE,'assertion failed',True))

 forwarded=source.replace('Relay.Forward(2);','Relay.Forward(limit);')
 result.append(('forwarded_payloads',forwarded,prop,'satisfied',True))
 computed=forwarded.replace('Hub.ReceivePrimary(2);','Hub.ReceivePrimary(limit + Round);')
 result.append(('computed_payloads',computed,TRUE,'satisfied',True))
 result.append(('computed_payload_property_error',computed,GLOBAL,'assertion failed',True))

 # Either actor can introduce a new parameter value into the other's selected set.
 mutual='''reactiveclass Node(5) {
    knownrebecs { Node peer; }
    Node() { self.tick(false); }
    msgsrv tick(boolean value) { peer.tick(!value); }
}
main { Node A(B):(); Node B(A):(); }
'''
 result.append(('mutual_variable_payload_fallback',mutual,TRUE,'satisfied',True))
 return result
