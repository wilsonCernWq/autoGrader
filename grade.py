import sys, os, time, platform, json, shutil
from subprocess import Popen, PIPE

# checking if the submission is over-due
def time_check(config, student, log):

    if platform.system() ==  'Darwin':
        commands = f'''
        cd {config.get('directory-root')}/{s}
        stat -f "%m" -t "%Y" {config.get('tarFileName')}
        '''
    else:
        commands = f'''
        cd {config.get('directory-root')}/{s}
        stat -c "%Y" {config.get('tarball-name')}
        '''
    
    total = config.get('max-score')

    proc = Popen('/bin/bash', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate(commands.encode('utf-8'))
    outs = out.decode('utf-8').strip().split('\n')
    errs = err.decode('utf-8').split('\n')

    due = config.get('due-time-stamp')
    hour = 3600
    
    try: # can update the rubric manually here
        if int(outs[0]) <= int(due)+hour*0:
            total = total
            errs.append('on time')
            print("On Time")
        elif int(outs[0]) > int(due)+hour*0 and int(outs[0]) <= int(due)+hour*1:
            total *= 0.9
            errs.append('late by 0+ hour')
            print("late by 0+ hour")
        elif int(outs[0]) > int(due)+hour*1 and int(outs[0]) <= int(due)+hour*2:
            total *= 0.8
            errs.append('late by 1+ hours')
            print("late by 1+ hour")
        elif int(outs[0]) > int(due)+hour*2 and int(outs[0]) <= int(due)+hour*3:
            total *= 0.7
            errs.append('late by 2+ hours')
            print("late by 2+ hour")
        elif int(outs[0]) > int(due)+hour*3 and int(outs[0]) <= int(due)+hour*4:
            total *= 0.6
            errs.append('late by 3+ hours')
            print("late by 3+ hour")
        else:
            total *= 0
            errs.append('late by 4+ hours')
            print("late by 4+ hour")
    except:
        print("Is it exception")
        pass

    total = int(total)
        
    log['submission-time'] = outs[0]
    log['submission-total'] = total
    log['log'] = errs

    return total

def reset_workdir(config, student, logfilename):
    # the student has been graded, skip
    if os.path.exists(logfilename):
        return False
    else: # reset the directory
        _dir = os.path.join(config.get('directory-work'), student)
        _src = os.path.join(config.get('directory-root'), student, config.get('tarball-name'))
        _dst = os.path.join(_dir, config.get('tarball-name'))
        try:
            shutil.rmtree(_dir, True) # delete the old one
            os.mkdir(_dir)            # recreate the new one
            shutil.copy(_src, _dst)
        except OSError:
            print("Resetting the directory %s failed" % _dir)
            raise
        else:
            print("Successfully reset the directory %s" % _dir)
        return True

# TODO
# should be able to resume work if possible
# save students' score one by one in separate, editable file
# collect grades in the final step

# start processing timer
start_time = time.time()

# load user setting
# TODO: configure file format here
with open('config.json') as f:
    config = json.load(f)
 
# initialize students
students = []

# prepare a list of all submitted students
ls_results, _ = Popen(['ls', config.get('directory-root')],
                      stdout=PIPE, stderr=PIPE,
                      encoding='utf8').communicate()
for item in ls_results.split(): 
    if '@' in item: # only consider kerberos@ad3.ucdavis.edu
        students.append(item)

#testInputFile = config.get('testInputFileName')

# put test input file in a list for partial checking
#testOutputList = [line.rstrip('\n') for line in open(config.get('testOutputFileName'), 'r')]

#results = []
#finalResults = []
#count = 0

for s in students:

    # the path of the record file
    stulog_filename = os.path.join(config.get('directory-work'), s + '.json')
    stulog = {}
    
    if reset_workdir(config, s, stulog_filename):

        print('\nworking on: %s' % s)
        
        stulog['time-check'] = {}
        total = time_check(config, s, stulog['time-check'])
        
        

    print(stulog)
    exit()
    
    #with open()
    
    # total = config.get('maxScore')
    # if platform.system() ==  'Darwin':
    #     commands = f'''
    #     cd {s}
    #     stat -f "%m" -t "%Y" {config.get('tarFileName')}
    #     tar xvf {config.get('tarFileName')}
    #     make all
    #     make clean
    #     make all
    #     '''
    # else:
    #     commands = f'''
    #     cd {s}
    #     stat -c "%Y" {config.get('tarFileName')}
    #     tar xvf {config.get('tarFileName')}
    #     make all
    #     make clean
    #     make all
    #     '''
    

    # # no multi file means 2 cases
    # # 1. either the executable requires no input
    # # 2. or it requires a single input file 
    # if not (config.get('isMultiFileInput')):
    #     if testInputFile == '':
    #         commandsExec = f'''
    #             cd {s}
    #             ./{config.get('execFileName')}
    #             '''
    #     else:
    #         commandsExec = f'''
    #             cd {s}
    #             ./{config.get('execFileName')} < {testInputFile}
    #             '''
    # else:
    #     maxInFile = config.get('multipleInFile')
    #     commandString = ""
    #     if maxInFile != 0:
    #         # form multiple input commanc strings
    #         for inFileCount  in range(1, maxInFile + 1):
    #             commandString = commandString + "./" + config.get('execFileName') + " < ../test" + str(inFileCount) + ".in\n"
    #         commandsExec = f'''
    #             cd {s}
    #             {commandString}
    #             '''
    #     else:
    #         print("No of Max File must be greater than 0")
    #         exit

    # runExecutable = Popen('/bin/bash', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    # out, err = runExecutable.communicate(commandsExec.encode('utf-8'))
    # outputsExec = out.decode('utf-8').strip().split('\n')
    # print(outputsExec)
    # errorsExec = err.decode('utf-8').split('\n')
    # errors.append(errorsExec)

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

# with open(config.get('verboseResultFileName'), 'w+') as f:
#     for result in results:
#         f.write(str(result)+'\n')
#     f.write(f'correct submissions: {str(count)}')
#     f.write(f'total submissions: {len(students)}')

# with open(config.get('resultsFileName'), 'w+') as f:
#     for finalResult in finalResults:
#         f.write(str(finalResult)+'\n')

print("Time to process", len(students), "students was %s seconds" % (time.time() - start_time))
