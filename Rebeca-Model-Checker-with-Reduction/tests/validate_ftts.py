#!/usr/bin/env python3
"""Compile actual array-expression and FTTS decision snippets, without Maven.
This complements, and does not replace, end-to-end model generation tests.
"""
import json
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
java = (root / 'src/main/java/org/rebecalang/rmc/corerebeca/translator/CoreRebecaTermPrimaryExpressionTranslator.java').read_text()
expr = java[java.index('retValue += "[([&]'):].split(';\n', 1)[0][len('retValue += '):]
expr = expr.replace('((ArrayType)termPrimary.getType()).getDimensions().get(indexCounter)', '"4"').replace('expression.getLineNumber()', '"7"').replace('statementTranslatorContainer.translate(expression, "")', '"INDEX"')
literals = re.findall(r'"(?:\\.|[^"\\])*"', expr)
assert re.sub(r'"(?:\\.|[^"\\])*"', '', expr).replace('+', '').strip() == ''
index = ''.join(json.loads(x) for x in literals)
ftts = (root / 'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
safety = ftts.split('    int rMsgId = ', 1)[1].split('#else', 1)[0]
safety = ('    int rMsgId = ' + safety).replace('$maxMsgIdPlusOne', '3')
terminal = ftts.split('    if (nextRebecTime == MAX_TIME) {', 1)[1].split('\n    if (result & NEW_STATE)', 1)[0]
terminal = '    if (nextRebecTime == MAX_TIME) {' + terminal
access = lambda i: 'q' + index.replace('INDEX', i)
source = r'''
#include <cassert>
#include <stdexcept>
#include <string>
#include <iostream>
using namespace std;
void assertion(bool ok, string) { if (!ok) throw out_of_range("index"); }
const string reactiveClassName="Test", methodName="array";
const int REBEC_COUNT=2, MAX_TIME=999;
struct Actor { unsigned char messageQueue[1]; const char* getName() { return "Test"; } } actors[2];
Actor* rebecs[2]={&actors[0], &actors[1]};
bool sdiPairs[2][3][2][3]={};
struct DeadlockException { DeadlockException(string) {} };
struct State { int stateID=1; };
State oldState, nextState;
struct Node { State* state; };
Node current={&oldState};
bool safe(int r) { SAFETY }

long finish(int nextRebecTime) {
    Node newState={&nextState}; (void)newState;
    long nonDetTrans=2; (void)nonDetTrans;
    TERMINAL_BLOCK
    return 3;
}
int main() {
    int q[4]={10,20,30,40}, i=1;
    ACCESS0 = ACCESS1;
    assert(q[0]==20);
    int value=ACCESSSIDE;
    assert(value==20 && i==2);
    q[2]=1;
    value=ACCESSNESTED;
    assert(value==20);
    for (int invalid : {-1,4}) {
        bool thrown=false;
        try { (void)ACCESSINVALID; } catch (out_of_range&) { thrown=true; }
        assert(thrown);
    }
    actors[0].messageQueue[0]=1;
    actors[1].messageQueue[0]=0;
    assert(safe(0));
    sdiPairs[0][1][1][2]=true;
    assert(!safe(0)); // Future dependent action, even with an empty queue.
    assert(finish(0)==3);
    bool thrown=false;
    try { finish(MAX_TIME); } catch (DeadlockException&) { thrown=true; }
    assert(thrown && current.state==&nextState);
}
'''.replace('SAFETY', safety).replace('TERMINAL_BLOCK', terminal)
for marker, idx in [('ACCESS0','0'),('ACCESS1','1'),('ACCESSSIDE','i++'),('ACCESSNESTED',access('2')),('ACCESSINVALID','invalid')]:
    source=source.replace(marker,access(idx))
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'test.cpp'; cpp.write_text(source)
    for opt in ['-O0','-O2']:
        for flags in [[],['-DPOR_DIAGNOSTICS']]:
            subprocess.run(['g++','-std=c++11',opt,'-Wall','-Wextra','-Werror',*flags,str(cpp),'-o',str(Path(tmp)/'test')],check=True)
            subprocess.run([str(Path(tmp)/'test')],check=True)
print('PASS: array assignment, nested/side-effect indices, bounds, future dependencies, deadlock stops execution (O0/O2)')
