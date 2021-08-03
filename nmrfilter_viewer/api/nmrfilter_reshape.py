import subprocess
import os
import sys

dr = sys.argv[1]
os.chdir('api')
subprocess.call(['python', './nmrfilter/nmrfilter.py', dr])
subprocess.call(['java', '-cp', './nmrfilter/*',
                 'uk.ac.dmu.simulate.Convert', dr])
cmd = ['python', './nmrfilter/respredict/predict_standalone.py',
       '--filename', os.path.join(dr, 'testall.smi'),
       '--format', 'sdf', '--nuc', '13C', '--sanitize', '--addhs', 'false',
       '>', os.path.join(dr, 'result/predc.json')]
os.system(' '.join(cmd))

cmd = ['python', './nmrfilter/respredict/predict_standalone.py',
       '--filename', os.path.join(dr, 'testall.smi'),
       '--format', 'sdf', '--nuc', '1H', '--sanitize', '--addhs', 'false',
       '>', os.path.join(dr, 'result/predh.json')]
os.system(' '.join(cmd))

subprocess.call(['java', '-cp', './nmrfilter/*',
                 'uk.ac.dmu.simulate.Simulate', dr])
subprocess.call(['python', './nmrfilter/nmrfilter2.py', dr])
