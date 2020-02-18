import sys, os, time, platform, json, shutil
from subprocess import Popen, PIPE


def record_message(arr, msg):
    arr.append(msg)
    print(msg)

    
def time_check(config, person): # checking if the submission is over-due

    _due     = int(config.get('due-time-stamp'))
    _tot     = int(config.get('max-score')) 
    _tarball = config.get('tarball')
    _workdir = os.path.join(config.get('dir-root'),
                            config.get('dir-submissions'),
                            person)
    
    if platform.system() == 'Darwin':
        _cmd = f'''
        cd {_workdir}
        stat -f "%m" -t "%Y" {_tarball}
        '''
    else:
        _cmd = f'''
        cd {_workdir}
        stat -c "%Y" {_tarball}
        '''

    _bash  = Popen('/bin/bash', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)        
    _o, _e = _bash.communicate(_cmd.encode('utf-8'))
    _outs  = _o.decode('utf-8').strip().split('\n')
    _errs  = _e.decode('utf-8').split('\n')

    _t = int(_outs[0])
    _hour = 3600
    
    try: # can update the rubric manually here
        print(_t)
        if _t <= _due+_hour*0:
            _tot = _tot
            record_message(_errs, 'on time')
        elif _t > _due + _hour*0 and _t <= _due + _hour*1:
            _tot *= 0.9
            record_message(_errs, 'late by 0+ hour')
        elif _t > _due + _hour*1 and _t <= _due + _hour*2:
            _tot *= 0.8
            record_message(_errs, 'late by 1+ hours')
        elif _t > _due + _hour*2 and _t <= _due + _hour*3:
            _tot *= 0.7
            record_message(_errs, 'late by 2+ hours')
        elif _t > _due + _hour*3 and _t <= _due + _hour*4:
            _tot *= 0.6
            record_message(_errs, 'late by 3+ hours')
        else:
            _tot *= 0
            record_message(_errs, 'late by 4+ hours')
    except:
        alert('Is it exception')
        raise
    
    ret = {}
    ret['adjusted-max-score'] = int(_tot)
    ret['timestamp'] = _t
    ret['messages'] = _errs
    return ret


def reset_workdir(config, person, logfilename):
    
    if os.path.exists(logfilename): # the student has been graded, skip
        return False
    else: # reset the directory
        _dir = os.path.join(config.get('dir-root'),
                            config.get('dir-work'),
                            person)
        _src = os.path.join(config.get('dir-root'),
                            config.get('dir-submissions'),
                            person,
                            config.get('tarball'))
        _dst = os.path.join(_dir, config.get('tarball'))
        try:
            shutil.rmtree(_dir, True) # delete the old one
            os.mkdir(_dir)            # recreate the new one
            shutil.copy(_src, _dst)
        except OSError:
            alert(f'Resetting the directory {_dir} failed')
            raise
        else:
            print(f'>> Successfully reset the directory {_dir}')
        return True


def question(msg):
    return input('%s%s%s' % ('\033[91m', msg, '\033[0m'))


def alert(msg):
    print('%s%s%s' % ('\033[91m', msg, '\033[0m'))

    
def message_filter(x): # filter function that removes empty strings
    if len(x) == 0:
        return False
    if 'Warning: File \'Makefile\' has modification time' in x:
        return False
    if 'warning:  Clock skew detected.' in x:
        return False
    return True

def process_job(config, job, person):
        
    # the command to run
    _workdir = os.path.join(config.get('dir-root'), config.get('dir-work'), person)
    _script  = os.path.join(config.get('dir-root'), job.get('file'))            
    _cmd     = f'''
    cd {_workdir}
    bash {_script} {config.get('tarball')}
    '''
    
    # run the command and gather outputs
    _bash  = Popen('/bin/bash', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)        
    _o, _e = _bash.communicate(_cmd.encode('utf-8'))
    _msg = []
    _msg += filter(message_filter, _o.decode('utf-8').strip().split('\n'))
    _msg += filter(message_filter, _e.decode('utf-8').split('\n'))
    
    # if there is no output and no errors, consider the result as a pass
    ret = {}
    if len(_msg) > 0:
        ret['deduct'] = -int(job.get('deduct'))
        for _item in _msg:
            print(_item)
        question('Failed, wish to handle manually?')            
    else:
        ret['deduct'] = 0
        print(f'pass {_script}')
    ret['messages'] = _msg
    return ret


def compute_score(config, person, record):
    score = int(record['check-time']['adjusted-max-score'])
    for k, v in record.items():
        if 'scripts' in k:
            score += int(v['deduct'])
    return score


# --------------------------------------------------------------------------------

# start processing timer
start_time = time.time()

# load user setting
with open('config.json') as f:
    config = json.load(f)
 
# initialize students
students = []

# prepare a list of all submitted students
ls_results, _ = Popen(['ls', os.path.join(config.get('dir-root'), config.get('dir-submissions'))],
                      stdout=PIPE, stderr=PIPE, encoding='utf8').communicate()
for item in ls_results.split(): 
    if '@' in item: # only consider kerberos@ad3.ucdavis.edu
        students.append(item)

# now grading one by one
for s in students:

    # the path of the record file
    filename = os.path.join(config.get('dir-root'),config.get('dir-work'), s + '.json')

    # the student has not been graded
    if reset_workdir(config, s, filename):

        print('>> working on student %s <<' % s)
        log = {}
    
        # step 1, we check the submission time
        log['check-time'] = time_check(config, s)
        
        # step 2, we iterate over all grading scripts
        for job in config.get('scripts'):
            name = job.get('file')
            log[name] = process_job(config, job, s)

        # step 3, save student's record
        print()
        json.dumps(log, indent=2)
        with open(filename, 'w') as outfile:
            json.dump(log, outfile, indent=2)

    # the student has been graded, thus we may skip
    else:
        
        with open(filename) as f:
            log = json.load(f)
        print('>> skip student %s <<' % s)    

    # check score
    question(f'Done!, score: {compute_score(config, s, log)}')
    print()
    
    #exit()
    
    # try:
    #     if outputsExec == testOutputList:
    #         outputs.append("Output is expected")
    #         results.append([s.split('@')[0], total, outputs, errors])
    #         kerberosID = s.split('@')[0]
    #         csvLine = kerberosID + ", " + str(total)
    #         finalResults.append(csvLine)
    #         count += 1
    #     else:
    #         if len(outputsExec) == len(testOutputList):
    #             for i in range(len(testOutputList)):
    #                 if testOutputList[i] != outputsExec[i]:
    #                     # deduct marks
    #                     outputs.append("Output is partially expected")
    #                     total -= config.get('deductScore')
    #         else:
    #             spaceRemovedOutputsExec = []
    #             for i in outputsExec:
    #                 j = i.replace(' ', '')
    #                 spaceRemovedOutputsExec.append(j)
    #             if spaceRemovedOutputsExec == testInputFile:
    #                 outputs.append("Output had extra spaces")
    #                 total -= 2*config.get('deductScore')
    #             else:
    #                 outputs.append("Output is completely different")
    #                 total += -10
    #         results.append([s.split('@')[0], total, outputs, errors])
    #         kerberosID = s.split('@')[0]
    #         csvLine = kerberosID + ", " + str(total)
    #         finalResults.append(csvLine)
    # except:
    #     total *= 0
    #     results.append([s.split('@')[0], total, outputs, errors])
    #     kerberosID = s.split('@')[0]
    #     csvLine = kerberosID + ", " + str(total)
    #     finalResults.append(csvLine)

print("Time to process", len(students), "students was %s seconds" % (time.time() - start_time))
