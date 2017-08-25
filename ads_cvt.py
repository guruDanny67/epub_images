#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2017 - Daniele Forghieri
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#

"""
Script to convert the book 'almanacco dello spazio' to have all the images
inside the epub file and not downloaded from internet on need
"""

import sys
import os
import re
import zipfile
from urllib.request import splittype, urlopen, ContentTooShortError
from urllib.error import URLError
import contextlib
import ssl

# we print some info 
verbose = 1
# list of (url, file) to download
img_to_download = []

# Regular expression to find the image url
find_img = re.compile('^(.*class="f".*)src="([^"]+)"(.*)$')

def extract(file_name, dest_dir):
    """
    Extract the epub/zip
    """ 
    with zipfile.ZipFile(file_name) as zf:
        print("Extracting '%s' to '%s' ..." % (file_name, dest_dir, ))
        zf.extractall(path=dest_dir)

def read_file(file_name):
    """
    Read a file e return a list with all the lines
    """
    with open(file_name, 'rb') as fi:
        rt = fi.readlines()

    return rt

def write_file(file_name, lst):
    """
    Write the list passed to the file, overwriting the original
    """
    with open(file_name, 'wb') as fo:
        for i in lst:
            fo.write(i)

def process_one_file(file_name):
    """
    Handle one file, checking for images
    """
    print("Processing '%s' ..." % (file_name, ))
    curf = read_file(file_name)

    # image(s) found ?
    nimg = 0
    # new file 
    newf = []
    # for all lines ..
    for i in curf:
        # it's a line with the image ?
        found = find_img.match(i.decode('utf-8'))
        if found:
            nimg += 1
            
            # c[0] is the part before the url, c[1] is the url (without the beginning 
            # src=" and the final ") and c[2] is the part after the url
            c = found.groups()
            
            # url to download
            url = c[1]
            # file to write, we drop what we don't need
            img_file = url
             
            # last / for path separator
            t = img_file.rfind('/')
            if t >= 0:
                img_file = img_file[t + 1:]
                
            # :orig or similar 
            t = img_file.find(':')
            if t >= 0:
                img_file = img_file[:t]

            # ?token or similar 
            t = img_file.find('?')
            if t >= 0:
                img_file = img_file[:t]
            
            # create the new line
            nl = c[0] + 'src="../Images/' + img_file + '"' + c[2]
            ##nl = c[0] + 'XXX=' + img_file + '"' + c[2]
            # encode to utf-8 for writing
            i = nl.encode('utf-8')
            if verbose:
                # deug to see if everything is ok 
                print(' > %s' % (url, ))
                print(' + %s' % (img_file, ))
            # add to the list of the downloads
            img_to_download.append( (url, img_file, ) )
        # add the line (original or converted)
        newf.append(i)

    if nimg:
        # url converted, write back the file
        write_file(file_name, newf)
    
def process_dir(dir_name):
    """
    Process all the .xhtml file in the directory
    """
    for cf in os.scandir(dir_name):
        if cf.is_file() and cf.name.lower().endswith('.xhtml'):
            process_one_file(os.path.join(dir_name, cf.name))

class Download(object):
    """
    Class to download one file from the url
    
    If the file exist locally and it's the same size of the remote one
    the download is skipped
    
    For url that doesn't returns the size the download is done every time
    
    First we try using the default o.s. authentication, with a permission error
    we retry without
    """  
    
    def __init__(self, url, file_name, header=''):
        self.url = url
        self.file_name = file_name
        self.header = header

        self._old_print = 0
        self._old_perc = 0
        self._downloading_file = '?'
        
    def download_progress(self, count, block_size, total_size):
        c_size = count * block_size
        if total_size > 0:
            # Percentage
            perc = (100 * c_size) // total_size
            if perc != self._old_perc:
                if perc > 100:
                    perc = 100
                self._old_perc = perc
                sp = ' %s (%u k) - %u%%' % (self._downloading_file, total_size / 1024, self._old_perc, )
                print(sp, end='\r')
                if len(sp) > self._old_print:
                    # Save the len to delete the line when we change file
                    self._old_print = len(sp)
        else:
            # Only the current, we don't know the size
            sp = ' %s - %u k' % (self._downloading_file, c_size / 1024, )
            print(sp, end='\r')
            if len(sp) > self._old_print:
                self._old_print = len(sp)

    def urlretrieve(self, url, filename, reporthook, ssl_ignore_cert=False):
        """
        Retrieve a URL into a temporary location on disk.

        Requires a URL argument. If a filename is passed, it is used as
        the temporary file location. The reporthook argument should be
        a callable that accepts a block number, a read size, and the
        total file size of the URL target. The data argument should be
        valid URL encoded data.

        If a filename is passed and the URL points to a local resource,
        the result is a copy from local file to new file.

        Returns True if the download is done 
        """
        url_type, _path = splittype(url)

        if ssl_ignore_cert:
            # ignore certificate
            ssl_ctx = ssl._create_unverified_context()
        else:
            # let the library does the work
            ssl_ctx = None

        msg = 'Opening %s ...' % (url, )
        print(msg, end='\r')
        with contextlib.closing(urlopen(url, None, context=ssl_ctx)) as fp:
            print('%*s' % (len(msg), '', ), end = '\r')
            headers = fp.info()
            if "content-length" in headers:
                size = int(headers["Content-Length"])
            else:
                size = -1
            
            do_read = True
            if size > 0 and os.path.isfile(filename):
                if os.path.getsize(filename) == size:
                    do_read = False
                    print(' Skipping file %s ...' % (filename, ))
                    result = False

            if do_read:
                with open(filename, 'wb') as tfp:
                    result = True
                    bs = 1024*8
                    read = 0
                    blocknum = 0
                    reporthook(blocknum, bs, size)
    
                    while True:
                        block = fp.read(bs)
                        if not block:
                            break
                        read += len(block)
                        tfp.write(block)
                        blocknum += 1
                        reporthook(blocknum, bs, size)

                if size >= 0 and read < size:
                    raise ContentTooShortError(
                        "retrieval incomplete: got only %i out of %i bytes"
                        % (read, size), result)

        return result

    def download(self):
        """
        Class main entry point
        """
        print("%sDownloading %s" % (self.header, self.url,))
        # Setup for progress show
        self._downloading_file = self.file_name
        self._old_perc = -1
        self._old_print = 0

        try:
            rt = self.urlretrieve(self.url, self.file_name, self.download_progress)
        except (ssl.SSLError, URLError) as e:
            print("Exception downloading file '%s'" % (self.file_name, ))
            print(e)
            rt = self.urlretrieve(self.url, self.file_name, self.download_progress, ssl_ignore_cert=True)

        if rt:
            print('%-*s' % (self._old_print, ' %s - Download finished' % (self.file_name, )), )

def make_zip(file_name, dir_name):
    """
    Add all the files presents in dir_name, recursively, 
    and create the new zip/epub
    """
    def _add_one_dir(dir_name, zf, skip_len):
        for cf in os.scandir(dir_name):
            full = os.path.join(dir_name, cf.name)
            if cf.is_dir():
                _add_one_dir(full, zf, skip_len)
            elif cf.is_file():
                zf.write(full, arcname=full[skip_len:])
    
    with zipfile.ZipFile(file_name, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        print('Creating file %s ...' % (file_name, ))
        _add_one_dir(dir_name, zf, len(dir_name))

def main():
    """
    Script main entry point
    """
    
    # Option parsing ...
    if len(sys.argv) == 2:
        # File name on the command line
        file_name = sys.argv[1]
    elif len(sys.argv) == 1:
        # default
        file_name = 'almanaccodellospazio.epub'
    else:
        # error
        print('Error. Specify one file or use the default')
        sys.exit(1)

    # extract the epub in a working dir
    work_dir = 'epub'
    extract(file_name, work_dir)

    # Analyze all the text files
    text = os.path.join(work_dir, 'OEBPS', 'Text')
    process_dir(text)
    
    # download all the images
    tot = len(img_to_download)
    cur = 0
    img_dir = os.path.join(work_dir, 'OEBPS', 'Images')
    for u, f in sorted(img_to_download):
        cur += 1
        cd = Download(u, os.path.join(img_dir, f), header='%u/%u ' % (cur, tot, ))
        cd.download()
        
    # make the new epub
    make_zip('almanaccodellospazio-immagini.epub', work_dir)

if __name__ == '__main__':
    main()
