#!/bin/bash


./maintenance < test4.in > tmp.out
diff tmp.out test4.out
rm -f tmp.out
