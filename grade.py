import os, time, platform, json, shutil
from subprocess import Popen, PIPE

# ------------------------------------------------------------------------------
# global variables
# ------------------------------------------------------------------------------

# load user setting
with open('config.json') as f:
    config = json.load(f)

rubrics = config['rubrics']


# ------------------------------------------------------------------------------
# functions
# ------------------------------------------------------------------------------

def print_rubrics():
    global rubrics
    for i, _ in enumerate(rubrics):
        print(i, end=' ')
        print(json.dumps(_, indent=4))


def add_rubric(deduct, comment):
    global rubrics
    r = {
        'deduct': int(deduct),
        'comment': comment
    }
    rubrics.append(r)
    with open('config.json', 'w') as out:
        json.dump(config, out, indent=2)


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
    due = int(config['due-time-stamp'])
    tot = int(config['max-score'])
    tar = config['tarball']
    work_dir = os.path.join(config['dir-root'], config['dir-submissions'], person)

    # we need a slightly different command for macos
    if platform.system() == 'Darwin':
        cmd = f'''
        cd {work_dir}
        stat -f "%m" -t "%Y" {tar}
        '''
    else:
        cmd = f'''
        cd {work_dir}
        stat -c "%Y" {tar}
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
        elif due + hour * 0 < t <= due + hour * 1:
            tot *= 0.9
            log_message(errs, 'late by 0+ hour')
        elif due + hour * 1 < t <= due + hour * 2:
            tot *= 0.8
            log_message(errs, 'late by 1+ hours')
        elif due + hour * 2 < t <= due + hour * 3:
            tot *= 0.7
            log_message(errs, 'late by 2+ hours')
        elif due + hour * 3 < t <= due + hour * 4:
            tot *= 0.6
            log_message(errs, 'late by 3+ hours')
        else:
            tot *= 0
            log_message(errs, 'late by 4+ hours')
    except:
        print_warning('Is it exception')
        raise

    ret = {
        'messages': errs,
        'timestamp': t,
        'adjusted-max-score': int(tot)
    }
    return ret


def reset_workdir(person):
    global config
    # reset the directory
    dst_dir = os.path.join(config['dir-root'], config['dir-work'], person)
    src_dir = os.path.join(config['dir-root'], config['dir-submissions'], person)
    src = os.path.join(src_dir, config['tarball'])
    dst = os.path.join(dst_dir, config['tarball'])
    try:
        shutil.rmtree(dst_dir, True)  # delete the old one
        os.mkdir(dst_dir)  # recreate the new one
        shutil.copy(src, dst)
    except OSError:
        print_warning(f'Resetting the directory {dst_dir} failed')
        raise
    else:
        print(f'>> Successfully reset the directory {dst_dir}')


def message_filter(x):  # filter function that removes empty strings
    if len(x) == 0:
        return False
    if 'Warning: File \'Makefile\' has modification time' in x:
        return False
    if 'warning:  Clock skew detected.' in x:
        return False
    return True


def process_job(task, person):
    # the command to run
    global config
    workdir = os.path.join(config.get('dir-root'), config.get('dir-work'), person)
    script = os.path.join(config.get('dir-root'), task.get('file'))
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
        ret['applied'] = False

    else:

        # the script failed
        print_warning(f'Failed {script} with Errors:')
        for _ in msg:
            print(_)
        ret['messages'] = msg

        # there is a default deduction rule
        deduct = int(task.get('deduct'))
        comment = task.get('comment')
        print_warning(f'Default rubric  = -{deduct}')
        print_warning(f'        comment = {comment}')

        # check if we should apply it
        ret['applied'] = 'y' not in question('Discard it?')

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

        # pause
        question('Continue?')

    return ret


def get_script(k):
    global config, rubrics
    for v in config['scripts']:
        if v['file'] == k:
            return v


def compute_score(rcd):
    global config, rubrics
    score = int(rcd['check-time']['adjusted-max-score'])
    comment = []
    for k, v in rcd.items():
        if 'scripts' in k:
            # apply default judgement
            if bool(v['applied']):
                score -= int(get_script(k)['deduct'])
                comment.append(get_script(k)['comment'])
            # check for rubrics
            if 'rubrics' in v:
                for r in v['rubrics']:
                    score += int(rubrics[r]['deduct'])
                    comment.append(rubrics[r]['comment'])
            # check for adjustments
            if 'user' in v:
                score += int(v['user']['deduct'])
                comment.append(v['user']['comment'])
    return max(score, 0), comment


def record(fname, obj, key, value):
    obj[key] = value
    with open(fname, 'w') as out:
        json.dump(obj, out, indent=2)


# ------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------

# start processing timer
start_time = time.time()

# initialize students
students = []

# prepare a list of all submitted students
results, _ = Popen(['ls', os.path.join(config['dir-root'], config['dir-submissions'])],
                   stdout=PIPE, stderr=PIPE, encoding='utf8').communicate()
for item in results.split():
    if '@' in item:  # only consider kerberos@ad3.ucdavis.edu
        students.append(item)

# now grading one by one
print()
for s in students:

    # the path of the record file
    filename = os.path.join(config['dir-root'], config['dir-work'], s + '.json')

    # the student has not been graded
    if os.path.exists(filename):
        with open(filename) as f:
            log = json.load(f)
    else:
        reset_workdir(s)
        log = dict()

    print('>> working on student %s <<' % s)

    # step 1, we check the submission time
    if 'check-time' not in log:
        record(filename, log, 'check-time', time_check(s))

    # step 2, we iterate over all grading scripts
    for job in config['scripts']:
        name = job['file']
        if name not in log:
            record(filename, log, name, process_job(job, s))

    # check score
    # print(json.dumps(log, indent=2))
    print_message(f'Done!, score: {compute_score(log)}')
    print()
    print()

print("Time to process", len(students), "students was %s seconds" % (time.time() - start_time))
