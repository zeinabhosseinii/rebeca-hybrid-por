import unittest
import xml.etree.ElementTree as ET
from audit_cell_register_graphs import signature,quotient

def state(messages):
 return ET.fromstring('<state atomicpropositions=""><rebec name="cell"><statevariables><variable name="Cell.value" type="int">0</variable></statevariables><queue>'+''.join('<message arrival="0" deadline="infinity" sender="worker">'+m+'</message>' for m in messages)+'</queue><now>0</now></rebec></state>')
class ProjectionChecks(unittest.TestCase):
 def test_parameters_and_multiplicity_retained(self):
  self.assertNotEqual(signature(state(['store(1)'])),signature(state(['store(2)'])))
  self.assertNotEqual(signature(state(['store(1)'])),signature(state(['store(1)','store(1)'])))
 def test_order_projection_is_explicit(self):
  a,b=state(['store(1)','store(2)']),state(['store(2)','store(1)'])
  self.assertEqual(signature(a),signature(b));self.assertNotEqual(signature(a,True),signature(b,True))
 def test_alias_with_missing_behavior_rejected(self):
  states={'a':state(['store(1)','store(2)']),'b':state(['store(2)','store(1)'])}
  with self.assertRaisesRegex(ValueError,'different action outcomes'):
   quotient(states,{'a':{('cell','STORE'):{'a'}},'b':{}})
 def test_timed_projection_rejected(self):
  s=state(['store(1)']);s.find('rebec/queue/message').set('arrival','1')
  with self.assertRaises(ValueError):signature(s)
if __name__=='__main__':unittest.main()
