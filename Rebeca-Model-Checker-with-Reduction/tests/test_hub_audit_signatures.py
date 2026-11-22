#!/usr/bin/env python3
"""Protect the exported-state comparison against misleading count/ID matches."""
import unittest
import xml.etree.ElementTree as ET
from audit_hub_alternatives import signature


def state(sid='1_0', sender='A', value='1', messages=('First()', 'Second()')):
    root=ET.Element('state', id=sid, atomicpropositions='')
    actor=ET.SubElement(root,'rebec',name='Hub')
    variables=ET.SubElement(actor,'statevariables')
    ET.SubElement(variables,'variable',name='x',type='int').text=value
    queue=ET.SubElement(actor,'queue')
    for msg in messages:
        ET.SubElement(queue,'message',sender=sender,arrival='0',deadline='infinity').text=msg
    ET.SubElement(actor,'now').text='0'
    return root


class Signatures(unittest.TestCase):
    def test_ids_are_not_state_contents(self):
        self.assertEqual(signature(state('1_0')),signature(state('99_0')))
    def test_unused_sender_projection(self):
        self.assertEqual(signature(state(sender='A')),signature(state(sender='B')))
    def test_queue_order_preserved(self):
        self.assertNotEqual(signature(state()),signature(state(messages=('Second()','First()'))))
    def test_variables_and_time_preserved(self):
        self.assertNotEqual(signature(state()),signature(state(value='2')))
        changed=state();changed.find('rebec/now').text='1'
        self.assertNotEqual(signature(state()),signature(changed))


if __name__=='__main__':unittest.main()
