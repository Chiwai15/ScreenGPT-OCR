
import sys
import traceback
import os

try:
    from main import main
    main()
except Exception as e:
    with open('error.log', 'w') as f:
        f.write(f'Error: {str(e)}\n')
        f.write('\nTraceback:\n')
        traceback.print_exc(file=f)
    print(f'Error occurred. Check error.log for details.')
    input('Press Enter to exit...')
