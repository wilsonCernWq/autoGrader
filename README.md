# autoGrader
1. <strong>Problem Description</strong>
    Attempts to reduce the task of manually grading over 190+ students C++ coding assignment submissions.\
    Students submit their programs via the handin command.\
    Each student has a folder containing the .tar file of all the related file to the assignment.\

2. <strong>Task</strong>
    1. Check the file submission date against the due date
    2. Untar the file
    3. Make the files
    4. Execute with the given input and save the result
    5. Check the result with given output


3. <strong>Usage</strong>
    ```console
    foo@bar:~$ python3 grade.py testInputFile.in testOutputFile.out
    ```
    The input file is not mandatory, in that case the script needs to be hardcoded to supply proper input.

4. <stong>Output</strong>
    1. A clean comma separated txt file with kerberosID, score
    2. A verbose commas separated txt file with kerberosID, Logs

5. <stong>Analysis</strong>
    This script was tested on a folder containing over 190 students sub-directories all containing .tar files.\
    Overall time it took was just over <strong>150 seconds</strong>, about <strong>2.5 - 3 minutes</strong>\
    The manual task on the other hand could take over 5 hours or more. :P
