#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import os
import re
import subprocess
import sys
from threading import Thread
import requests
import time
import concurrent.futures
from multiprocessing import Queue
from multiprocessing import Lock
from pprint import pprint
from lxml import html

# Threads waiting to process
processing_queue = Queue(5000)
processing_finished = False
print_lock = Lock()

## Grab a URL from a moss call
## Regex Source:
##
## http://stackoverflow.com/questions/6883049/
##      regex-to-find-urls-in-string-in-python
def get_url(response):
    urls = \
        re.findall("""http[s]?://(?:[a-zA-Z]|
            [0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F]
            [0-9a-fA-F]))+"""
                   , response)
    if len(urls) > 0:
        # Only one URL should be returned
        return urls[0]
    else:
        # No results in URL - bad request
        raise ValueError("No URL")


## Get all percentages from a moss URL
def get_percentages(url):
    # Get page content
    page = requests.get(url)
    content = page.content
    # Find percent in content 
    percentages = re.findall('[0-9]+%', content)
    return percentages


## Scrape a moss URL to find the highest percentage match
def get_high_percentages(url, cutoff):
    # No high values by default
    high_score = False
    percentages = get_percentages(url)
    # Search through resulting percentages for values past cutoff
    if len(percentages) > 0:
        for score in percentages:
            score = int(score.strip('%'))
            if score > cutoff:
                # High value result
                high_score = True
    return high_score


## Process queue
def process_queue():
    global processing_finished
    global processing_queue


    try:
        while (True):
            row = processing_queue.get()
            if (row.has_key("finished_processing")):
                print "Finished processing."
                break
            else:
                compare_files(row["new_file"], row["old_file"], row["output_filename"])
    except KeyboardInterrupt:
        print "MEH"
        raise

## See if two files should be compared. Compare them if they are
def compare_files(_old, _new, output_filename):
    global print_lock

    cutoff = 50

    try:
        matches = []

        for root, dirnames, filenames in os.walk(_old):
            for filename in filenames:
                if filename.endswith(('.php', '.js', '.css', '.html', '.py', '.txt')):
                    matches.append(os.path.join(root, filename))
        for root, dirnames, filenames in os.walk(_new):
            for filename in filenames:
                if filename.endswith(('.php', '.js', '.css', '.html', '.py', '.txt')):
                    matches.append(os.path.join(root, filename))

        moss_arguments = ['moss/moss']
        moss_arguments.extend(matches)
        response = subprocess.check_output()

        url = get_url(response)

        high_score = get_high_percentages(url, cutoff)
        if high_score:
            percentages = get_percentages(url)
            print '****************'
            print '***** ALERT ****'
            print '****************'
            print _new
            print _old
            for _score in percentages:
                print _score
            print url
            with open(output_filename, 'a') as file:
                file.write('******' + '\n')
                file.write(_new + '\n')
                file.write(_old + '\n')
                file.write(url + '\n')
                for _score in percentages:
                    file.write(str(_score) + '\n')
        else:
	        print_lock.acquire()
	        print 'Okay: ' + url + "\n"
	        print_lock.release()
    except Exception as e:
        print "Exception"
        pass
    print "Returning"
    return


## Send moss request
def moss_compare(new_dirs, old_dirs):
    global processing_queue
    global processing_finished

    try:
        # Write output to file
        output_filename = sys.argv[1] + '_comp_' + sys.argv[2] + '.txt'
        # print 'Writing output to ' + output_filename

        # For loop: m * n filepaths
        for _new in new_dirs:
            for _old in old_dirs:
                processing_queue.put({"new_file": _new,
                    "old_file": _old,
                    "output_filename": output_filename})

        print "Queue populated. Approximately " + str(processing_queue.qsize()) + " in queue"

        processing_queue.put({
            "finished_processing": True
        })

        # Start threads
        num_worker_threads = 4
        for i in range(num_worker_threads):
            t = Thread(target=process_queue)
            t.daemon = True
            t.start()
            print "Started thread " + str(i)

        

    except KeyboardInterrupt as e:
        print "cancelled"
        processing_finished = True
        sys.exit(0)


## Grab file extension
def get_extension(file_path):
    extension = os.path.splitext(file_path)[1]
    return extension


## Return files with matched name
def walk(substring):
    matched_files = []
    _dir = os.getcwd() + '/repositories'

    for subdirectory in os.listdir(_dir):
        path = os.path.join(_dir, subdirectory)
        if substring in path:
            matched_files.append(path)

    return matched_files


## Usage
def printUsage():
    print 'USAGE:'
    print 'python file-walker.py [new modules] [old modules]'
    print "  Grab files whose full path contains the given substring, such as 'spring2015-module1'"


## MAIN
if __name__ == '__main__':
    if len(sys.argv) > 2:
        old_files = walk(sys.argv[1])
        print 'Grabbed ' + str(len(old_files)) + ' old directories'

        new_files = walk(sys.argv[2])
        print 'Grabbed ' + str(len(new_files)) + ' new directories'
        moss_compare(new_files, old_files)
    else:
        printUsage()

      