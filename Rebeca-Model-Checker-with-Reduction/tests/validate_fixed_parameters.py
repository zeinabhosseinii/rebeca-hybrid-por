#!/usr/bin/env python3
"""Native full/reduced comparisons, including positive scaling and first-error runs."""
import fixed_parameter_models as models
import validate_communicating_properties as driver

def main():
 driver.cases=models.cases
 driver.main()
if __name__=='__main__':main()
