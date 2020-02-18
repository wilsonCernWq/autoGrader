import sys, os, time, platform, json, shutil
from subprocess import Popen, PIPE

# ------------------------------------------------------------------------------
# global variables
# ------------------------------------------------------------------------------

# load user setting
with open('config.json') as f:
    config = json.load(f)

rubrics = config.get('rubrics')
rmanual = {}


# ------------------------------------------------------------------------------
# functions
# ------------------------------------------------------------------------------

def print_rubrics():
    global rubrics
    for i, item in enumerate(rubrics):
        print(i, end=' ')
        print(json.dumps(item, indent=4))


def add_rubric(deduct, comment):
    global rubrics
    global rmanual
    r = {
        'deduct': int(deduct),
        'comment': comment
    }
    rubrics.append(r)
    rmanual.append(r)
    return len(rubrics) - 1


# def get_rubric(index):
#    return rubrics[index]


def log_message(arr, msg):
    arr.append(msg)
    print(msg)


def question(msg):
    return input('%s%s%s ' % ('\033[91m', msg, '\033[0m'))


def print_warning(msg):
    print('%s%s%s' % ('\033[91m', msg, '\033[0m'))


def print_message(msg):
    print('%s%s%s' % ('\033[92m', msg, '\033[0m'))


def time_check(person):  # checking if the submission is over-due
    # user defined variables
    global config
    due = int(config.get('due-time-stamp'))
    tot = int(config.get('max-score'))
    tarball = config.get('tarball')
    workdir = os.path.join(config.get('dir-root'), config.get('dir-submissions'), person)

    # we need a slightly different command for macos
    if platform.system() == 'Darwin':
        cmd = f'''
        cd {workdir}
        stat -f "%m" -t "%Y" {tarball}
        '''
    else:
        cmd = f'''
        cd {workdir}
        stat -c "%Y" {tarball}
        '''

    # run it
    bash = Popen('/bin/bash', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    o, e = bash.communicate(cmd.encode('utf-8'))
    outs = o.decode('utf-8').strip().split('\n')
    errs = e.decode('utf-8').split('\n')
    t = int(outs[0])
    hour = 3600

    # can update the rubric manually here
    try:
        print(t)
        if t <= due + hour * 0:
            tot = tot
            log_message(errs, 'on time')
        elif t > due + hour * 0 and t <= due + hour * 1:
            tot *= 0.9
            log_message(errs, 'late by 0+ hour')
        elif t > due + hour * 1 and t <= due + hour * 2:
            tot *= 0.8
            log_message(errs, 'late by 1+ hours')
        elif t > due + hour * 2 and t <= due + hour * 3:
            tot *= 0.7
            log_message(errs, 'late by 2+ hours')
        elif t > due + hour * 3 and t <= due + hour * 4:
            tot *= 0.6
            log_message(errs, 'late by 3+ hours')
        else:
            tot *= 0
            log_message(errs, 'late by 4+ hours')
    except:
        print_warning('Is it exception')
        raise

    ret = {}
    ret['messages'] = errs
    ret['timestamp'] = t
    ret['adjusted-max-score'] = int(tot)
    return ret


def reset_workdir(person, filename):
    global config
    if os.path.exists(filename):  # the student has been graded, skip
        return False
    else:  # reset the directory
        dstdir = os.path.join(config.get('dir-root'), config.get('dir-work'), person)
        srcdir = os.path.join(config.get('dir-root'), config.get('dir-submissions'), person)
        src = os.path.join(srcdir, config.get('tarball'))
        dst = os.path.join(dstdir, config.get('tarball'))
        try:
            shutil.rmtree(dstdir, True)  # delete the old one
            os.mkdir(dstdir)  # recreate the new one
            shutil.copy(src, dst)
        except OSError:
            print_warning(f'Resetting the directory {dstdir} failed')
            raise
        else:
            print(f'>> Successfully reset the directory {dstdir}')
        return True


def message_filter(x):  # filter function that removes empty strings
    if len(x) == 0:
        return False
    if 'Warning: File \'Makefile\' has modification time' in x:
        return False
    if 'warning:  Clock skew detected.' in x:
        return False
    return True


def process_job(job, person):
    # the command to run
    global config
    workdir = os.path.join(config.get('dir-root'), config.get('dir-work'), person)
    script = os.path.join(config.get('dir-root'), job.get('file'))
    cmd = f'''
    cd {workdir}
    bash {script} {config.get('tarball')}
    '''

    # run the command and gather outputs
    bash = Popen('/bin/bash', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    o, e = bash.communicate(cmd.encode('utf-8'))
    msg = []
    msg += filter(message_filter, o.decode('utf-8').strip().split('\n'))
    msg += filter(message_filter, e.decode('utf-8').split('\n'))

    # if there is no output and no errors, consider the result as a pass
    ret = {}
    if len(msg) == 0:

        # the script passed
        print(f'pass {script}')
        ret['deduct'] = 0

    else:

        # the script failed
        print_warning(f'Failed {script} with Errors:')
        for item in msg:
            print(item)
        ret['messages'] = msg

        # there is a default deduction rule
        deduct = int(job.get('deduct'))
        comment = job.get('comment')
        print_warning(f'Default rubic   = -{deduct}')
        print_warning(f'        comment = {comment}')
        if 'y' in question('Discard it?'):
            ret['deduct'] = 0
        else:
            ret['deduct'] = -deduct
            ret['comment'] = comment

        # check if we want to apply a rubric
        if 'y' in question('Apply other rubrics?'):
            ret['rubrics'] = []

            # apply existing rubrics
            print_rubrics()
            while True:
                select = question(f'Select a rubric?')
                if not select:
                    break
                ret['rubrics'].append(int(select))

            # define a new rubric here and apply it
            while 'y' in question(f'Create a new rubric?'):
                ret['rubrics'].append(add_rubric(int(question(f'      deduct  =')),
                                                 question(f'      comment =')))

            # adjust the score manually
            if 'y' in question(f'Manually adjust deduction?'):
                user = {
                    'deduct': int(question(f'  deduct  =')),
                    'comment': question(f'  comment =')
                }
                ret['user'] = user

    return ret


def compute_score(person, record):
    global config, rubrics
    score = int(record['check-time']['adjusted-max-score'])
    comment = []
    for k, v in record.items():
        if 'scripts' in k:
            # apply default judgement
            score += int(v['deduct'])
            if 'comment' in v:
                comment.append(v['comment'])
            # check for rubrics
            if 'rubrics' in v:
                for r in v['rubrics']:
                    score += int(rubrics[r]['deduct'])
                    comment.append(rubrics[r]['comment'])
            # check for adjustments
            if 'user' in v:
                score += int(v['user']['deduct'])
                comment.append(v['user']['comment'])
    return score, comment


# ------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------

# start processing timer
start_time = time.time()

# initialize students
students = []

# prepare a list of all submitted students
results, _ = Popen(['ls', os.path.join(config.get('dir-root'), config.get('dir-submissions'))],
                   stdout=PIPE, stderr=PIPE, encoding='utf8').communicate()
for item in results.split():
    if '@' in item:  # only consider kerberos@ad3.ucdavis.edu
        students.append(item)

# now grading one by one
print()
for s in students:

    # the path of the record file
    filename = os.path.join(config.get('dir-root'), config.get('dir-work'), s + '.json')

    # the student has not been graded
    if reset_workdir(s, filename):

        print('>> working on student %s <<' % s)

        # step 1, we check the submission time
        log = {
            'check-time': time_check(s)
        }

        # step 2, we iterate over all grading scripts
        for job in config.get('scripts'):
            name = job.get('file')
            log[name] = process_job(job, s)

        # step 3, save student's record
        print()
        with open(filename, 'w') as outfile:
            json.dump(log, outfile, indent=2)

    # the student has been graded, thus we may skip
    else:

        with open(filename) as f:
            log = json.load(f)
        print('>> skip student %s <<' % s)

        # check score
    # - print(json.dumps(log, indent=2))
    question(f'Done!, score: {compute_score(s, log)}')
    print()
    print()

print("Time to process", len(students), "students was %s seconds" % (time.time() - start_time))
