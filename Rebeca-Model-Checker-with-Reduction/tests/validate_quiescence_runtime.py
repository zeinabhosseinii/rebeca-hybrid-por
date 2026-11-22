#!/usr/bin/env python3
"""Compile the actual generated LoadBalancer safety function with queue controls."""
from pathlib import Path
import argparse
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('generated', type=Path)
a = p.parse_args()
s = (a.generated / 'TimedModelChecker.cpp').read_text()
start = s.index('bool TimedModelChecker::areActiveActionsSafe(')
end = s.index('\nint TimedModelChecker::chooseIsolatedLocalAlternative', start)
function = s[start:end]
source = r'''
#include <cassert>
#include <iostream>
using namespace std;
const int REBEC_COUNT=6;
struct Actor {
    unsigned char messageQueue[5]={};
    int maxQueueLength=5;
    const char* getName() { return "Test"; }
};
Actor actors[6]; Actor* rebecs[6]={&actors[0],&actors[1],&actors[2],&actors[3],&actors[4],&actors[5]};
struct State { int stateID=1; } state;
struct Current { State* state; } current={&state};
using byte=unsigned char;
struct TimedModelChecker { bool areActiveActionsSafe(byte*,int,int); };
FUNCTION
int main() {
    TimedModelChecker checker;
    // LoadBalancer main order: Hub, two relays, two sources, Bootstrapper.
#if defined(POR_DISABLE_QUIESCENCE) || defined(TEST_GATED)
    assert(!checker.areActiveActionsSafe(nullptr,0,1));
#else
    assert(checker.areActiveActionsSafe(nullptr,0,1));
    // Pending at head, or behind another message / scheduled for the future.
    actors[5].messageQueue[0]=1;
    assert(!checker.areActiveActionsSafe(nullptr,0,1));
    actors[5].messageQueue[0]=0;
    actors[5].messageQueue[4]=1;
    assert(!checker.areActiveActionsSafe(nullptr,0,1));
    actors[5].messageQueue[4]=0;
    assert(checker.areActiveActionsSafe(nullptr,0,1));
#endif
    // Hub handlers CAN be sent again. Their absent queues do not certify them.
    assert(!checker.areActiveActionsSafe(nullptr,5,1));
}
'''.replace('FUNCTION', function)
with tempfile.TemporaryDirectory() as d:
    d=Path(d); cpp=d/'test.cpp';cpp.write_text(source)
    for opt in ('-O0','-O2'):
        for flags in ([], ['-DPOR_DIAGNOSTICS'], ['-DPOR_DISABLE_QUIESCENCE'], ['-DTEST_GATED']):
            cpp.write_text(source.replace('if (true && neverSent', 'if (false && neverSent') if '-DTEST_GATED' in flags else source)
            subprocess.run(['g++','-std=c++11',opt,*flags,str(cpp),'-o',str(d/'test')],check=True)
            subprocess.run([str(d/'test')],check=True)
print('PASS: generated function; empty, pending head/tail, possible resend, disabled control (O0/O2)')
