#!/usr/bin/env python3
"""Native differential checks for fixed and mixed payloads."""
import communicating_property_models as models
import validate_communicating_properties as driver
base=models.cases()
def variants():
 result=[]
 for key in (0,4,6):
  name,source,prop,outcome,_=base[key]
  source=source.replace('Dispatch()', 'Dispatch(int ignored)')
  source=source.replace('.Dispatch(int ignored)', '.Dispatch(7)')
  result.append(('unused_'+name,source,prop,outcome,True))
 name,source,prop,outcome,_=result[0]
 source=source.replace('Cycle = Cycle + 1;', 'Cycle = Cycle + ignored;',1)
 result.append(('observed_parameter',source,prop,'satisfied',True))
 name,source,prop,outcome,_=result[0]
 source=source.replace('PrimarySrc.Dispatch(7);','PrimarySrc.Dispatch(9);',1)
 result.append(('different_unread_payloads',source,prop,outcome,True))
 return result
driver.cases=variants
if __name__=='__main__':driver.main()
