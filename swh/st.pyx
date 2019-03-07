"""This is a cython wrapper for compiling strategy so.

To compile multiple python files in strategy so, add the following statement:
    >> include "my_module.py"
after the line
    >> include "api.py"
for each of your additional python modules.

- Note:
    1. Import statements should be removed from these modules, or ImportError exceptions must be handled.
    2. Modules must be included in the correct order to meet code dependency.

For any additional information regarding cython, please refer to http://cython.org/
"""
# ============== DO NOT MODIFY ==============
include "api.py"
# ======= ADD MODULES BEYOND THIS LINE =======
include "st.py"
