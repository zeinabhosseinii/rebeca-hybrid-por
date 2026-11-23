"""A local, pure assertion can still need dependent deferred actions."""
from action_por_reference import Graph
from audit_both_reductions import every_cycle_has_full_state

def check():
    read=('Actor','Check');write=('Actor','Set');idle=('Actor','Idle')
    graph=Graph();graph.initial='s'
    for s,a,t in [('s',read,'c'),('s',write,'w'),('c',write,'d'),('w',read,'error'),('d',idle,'d')]:graph.add(s,a,t)
    graph.observations={s:('assertion failed' if s=='error' else '') for s in graph.edges}
    # Check asserts x==0. Set writes x=1. Selecting Check first hides the
    # Set->Check error. Its remaining cycle is nevertheless a full Idle loop.
    selected={'s':{read:{'c'}},'c':{write:{'d'}},'d':{idle:{'d'}}}
    assert every_cycle_has_full_state(set(selected),selected,{'c','d'})
    ok,evidence=graph.certify('s',read)
    assert not ok and evidence['reason']=='diamond_failed',evidence
    return {'pure_local_counterexample':'rejected','strong_cycle_alone_passes':True,'failure':evidence}

if __name__=='__main__':print(check())
