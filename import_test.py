import sys
print('sys.path:', sys.path)

# pycausalimpact
try:
    import pycausalimpact
    print('pycausalimpact: import OK')
except Exception as e:
    print('pycausalimpact: import FAILED:', e)

# causalimpact
try:
    import causalimpact
    print('causalimpact: import OK')
except Exception as e:
    print('causalimpact: import FAILED:', e)

# from pycausalimpact import CausalImpact
try:
    from pycausalimpact import CausalImpact
    print('from pycausalimpact import CausalImpact: OK')
except Exception as e:
    print('from pycausalimpact import CausalImpact: FAILED:', e)

# from causalimpact import CausalImpact
try:
    from causalimpact import CausalImpact
    print('from causalimpact import CausalImpact: OK')
except Exception as e:
    print('from causalimpact import CausalImpact: FAILED:', e) 