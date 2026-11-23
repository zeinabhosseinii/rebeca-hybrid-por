"""Product models: independent actor-local cycles and a cross-actor state property."""
def model(n=3,bound=2,fault=False,terminating=False,cross=False):
 body='value = value + 1; if (value > '+str(bound)+') { value = 0; }'
 if fault:body+=' assertion(value < '+str(bound)+');'
 if not terminating:body+=' self.tick();'
 if cross:body+=' peer.tick();'
 return 'reactiveclass Node(3) { '+('knownrebecs { Node peer; }' if cross else '')+' statevars { int value; } Node() { value = 0; self.tick(); } msgsrv tick() { '+body+' } }\nmain { '+ ' '.join('Node N'+str(i)+(' (N'+str((i+1)%n)+')' if cross else '()')+':();' for i in range(n))+' }\n'
def property_text(bound=2,bad=False):
 return 'property { Assertion { Check: '+('!(N0.value == 1 && N1.value == 0)' if bad else 'N0.value >= 0 && N0.value <= '+str(bound))+'; } }\n'

def deferred_error_model():
 text=model(3).replace('int value;','int value; boolean failing;').replace('Node() {','Node(boolean bad) { failing = bad;').replace('msgsrv tick() {','msgsrv tick() { assertion(!failing || value < 1);')
 for i in range(3):text=text.replace('N'+str(i)+'():();','N'+str(i)+'():('+('true' if i==2 else 'false')+');')
 return text
