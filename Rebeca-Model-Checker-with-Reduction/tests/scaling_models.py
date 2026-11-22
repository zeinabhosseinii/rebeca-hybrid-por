"""Cyclic bounded epochs: finite per-worker work and mandatory global completion."""
def make_model(family,n,period=3):
    if n<1 or n>16 or period<2:raise ValueError('Require 1..16 workers and period >= 2')
    if family not in ('independent','shared'):raise ValueError(family)
    classes=[]
    for i in range(n):
        advance='self.Tick();' if family=='independent' else f'H.Step{i}();'
        classes.append(f'''reactiveclass Worker{i}(2) {{
 knownrebecs {{ Hub H; }}
 statevars {{ int cycle; }}
 Worker{i}() {{ cycle=0; self.Tick(); }}
 msgsrv Tick() {{ cycle=cycle+1; if(cycle<{period}) {{ {advance} }} else {{ cycle=0; H.Finish{i}(); }} }}
}}
''')
    classes.append(f'reactiveclass Hub({n+1}) {{\n knownrebecs {{ '+''.join(f'Worker{i} W{i}; ' for i in range(n))+'}\n statevars { int done; int count; }\n Hub() { done=0; count=0; }\n')
    restart=''.join(f'W{i}.Tick(); ' for i in range(n))
    for i in range(n):
        if family=='shared':classes.append(f' msgsrv Step{i}() {{ count=count+1; if(count>={period}) count=0; W{i}.Tick(); }}\n')
        classes.append(f' msgsrv Finish{i}() {{ done=done+1; if(done=={n}) {{ done=0; {restart} }} }}\n')
    classes.append('}\nmain {\n Hub H('+', '.join(f'W{i}' for i in range(n))+'):();\n')
    classes.extend(f' Worker{i} W{i}(H):();\n' for i in range(n))
    return '// Bounded per-worker work; next epoch starts only after every Finish.\n'+''.join(classes)+'}\n'
