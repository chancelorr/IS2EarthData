#!/bin/zsh

# input serial coordinates
# outputs list of lon/lat pairs in specified order

#CCW
awk -F",0 " '{for(i=0;i<(NF);i++) print $(i+1)}' | 
	awk -F"," '{print $1,",",$2,","}' | 
	tr -d ' ' | tr -d '\n' | sed '$ s/.$//'

#CW
#awk -F",0 " '{for(i=NF;i>0;i--) print $(i)}' | awk -F"," '{print $1, $2}'
