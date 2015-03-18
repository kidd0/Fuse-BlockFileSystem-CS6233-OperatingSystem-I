
#!/usr/bin/env python

# My file system checker - vn513

import sys
import os
import stat
import runonce

# We need lind_test_server.py, lind_fs_calls.py and lind_fs_constants.py.
# They should be in the REPY_PATH OR copy them in to this folder so python
# can import the lind_test_server

# add repy install path to script
repy_path = os.getenv("REPY_PATH")

if repy_path == None:
    # if not set, use the location of this file.
    (lind_fuse_path, name) = os.path.split(os.path.abspath(__file__))
    os.environ['REPY_PATH'] = lind_fuse_path
    code_path = lind_fuse_path
else:
    # If it is set, use the standard lind path
    code_path = os.path.join(repy_path, "repy/")

sys.path.append(code_path)



# change dir so the execfile in test server works
pwd = os.getcwd()
os.chdir(code_path)
import lind_test_server as lind
# and now back to where we started.
os.chdir(pwd)



import emulcomm
import emulfile
import emulmisc
import emultimer
import serialize


# Try push these into constants file
metadatafilename = 'lind.metadata'

FILEDATAPREFIX = 'linddata.'

MAXFILESIZE = 1638400



ROOTDIRECTORYINODE = 26

DIRECTORYPREFIX = 'D'

FILEPREFIX = 'F'

BLOCKSIZE = 4096

MAXNOOFBLOCKS = 10000

MAXNOOFPOINTERININDEX = int(MAXFILESIZE / BLOCKSIZE)

MAXFREEPOINTERBLOCKS = int(MAXNOOFBLOCKS / MAXNOOFPOINTERININDEX)


filesystemmetadata = {}

freeBlock = {}

superBlock = {}

fastinodelookuptable = {}

# contains open file descriptor information... (keyed by fd)
filedescriptortable = {}

# contains file objects... (keyed by inode)
fileobjecttable = {}

# I use this so that I can assign to a global string (currentworkingdirectory)
# without using global, which is blocked by RepyV2
fs_calls_context = {}

# Where we currently are at...

fs_calls_context['currentworkingdirectory'] = '/'


def restore_metadata(metadatafilename):
  # should only be called with a fresh system...
  assert(filesystemmetadata == {})
  filesystemmetadata['freeBlock'] = {}
  filesystemmetadata['inodetable'] = {}

# sort the file based on their file names its good to restore in order
  files = []
  for each_file in emulfile.listfiles():
    if FILEDATAPREFIX in each_file:
      # checks if the file contains linddata
      files.append(each_file)
  # sorting the files based on the value of X in linddata.X
  files.sort(key = lambda x: int(x.split(".")[1]))
  print files
  for filename in files:

    # restore free blocks
    metadatafo = emulfile.emulated_open(filename,True)
    metadatastring = metadatafo.readat(None, 0)
    metadatafo.close()
    # restore only inode, directory, freeblock and superblock block others are just data blocks that we can ignore
    try:
      desiredmetadata = serialize.deserializedata(metadatastring)
      block_no = int(filename.split('.')[1])
			# if the block is a SUPER BLOCK 
      if block_no == 0:
        filesystemmetadata['superBlock'] = desiredmetadata
			# If the block is a freeblock storage block
      elif block_no >=1 and block_no <= 24:
        filesystemmetadata['freeBlock'][block_no] = desiredmetadata
     # if the block contains data
      elif block_no > 24:
        if 'location' in desiredmetadata or 'filename_to_inode_dict' in desiredmetadata:
          filesystemmetadata['inodetable'][block_no] = desiredmetadata
    except Exception:
      print "Exception in the loop"
      pass
  _rebuild_fastinodelookuptable()

# I'm already added.
# taken from the fs_calls_
# change the inode - value pickup using a dict
def _recursive_rebuild_fastinodelookuptable_helper(path, inode):

  # for each entry in my table...
  for entryname,entryinode in filesystemmetadata['inodetable'][inode]['filename_to_inode_dict'].iteritems():

    # ignore the initial F,D prefix
    entryname = entryname[1:]
    # if it's . or .. skip it.
    if entryname == '.' or entryname == '..':
      continue

    # always add it...
    entrypurepathname = _get_absolute_path(path+'/'+entryname)
    fastinodelookuptable[entrypurepathname] = entryinode

    # and recurse if a directory...
    if 'filename_to_inode_dict' in filesystemmetadata['inodetable'][entryinode]:

      _recursive_rebuild_fastinodelookuptable_helper(entrypurepathname,entryinode)


def _rebuild_fastinodelookuptable():
  # first, empty it...
  for item in fastinodelookuptable:
    del fastinodelookuptable[item]
  # now let's go through and add items...

  # I need to add the root.
  fastinodelookuptable['/'] = ROOTDIRECTORYINODE
  # let's recursively do the rest...

  _recursive_rebuild_fastinodelookuptable_helper('/', ROOTDIRECTORYINODE)



# private helper function that converts a relative path or a path with things
# like foo/../bar to a normal path.
def _get_absolute_path(path):

  # should raise an ENOENT error...
  if path == '':
    return path

  # If it's a relative path, prepend the CWD...
  if path[0] != '/':
    path = fs_calls_context['currentworkingdirectory'] + '/' + path


  # now I'll split on '/'.   This gives a list like: ['','foo','bar'] for
  # '/foo/bar'
  pathlist = path.split('/')

  # let's remove the leading ''
  assert(pathlist[0] == '')
  pathlist = pathlist[1:]

  # Now, let's remove any '.' entries...
  while True:
    try:
      pathlist.remove('.')
    except ValueError:
      break

  # Also remove any '' entries...
  while True:
    try:
      pathlist.remove('')
    except ValueError:
      break

  # NOTE: This makes '/foo/bar/' -> '/foo/bar'.   I think this is okay.

  # for a '..' entry, remove the previous entry (if one exists).   This will
  # only work if we go left to right.
  position = 0
  while position < len(pathlist):
    if pathlist[position] == '..':
      # if there is a parent, remove it and this entry.
      if position > 0:
        del pathlist[position]
        del pathlist[position-1]

        # go back one position and continue...
        position = position -1
        continue

      else:
        # I'm at the beginning.   Remove this, but no need to adjust position
        del pathlist[position]
        continue

    else:
      # it's a normal entry...   move along...
      position = position + 1


  # now let's join the pathlist!
  return '/'+'/'.join(pathlist)


# private helper function
def _get_absolute_parent_path(path):
  return _get_absolute_path(path+'/..')

def verify_device_id():
  device_id = filesystemmetadata['superBlock']['devId']
  if (device_id != 20):
    print "The device ID is corrupt and is not 20"

def validate_free_blocks():
  free_block_count = 0
  for x in range(1, 25):
    try:
      temp_fo = fileopen(FILEDATAPREFIX+str(x), False)
      dict_serialized = temp_fo.readat(None,0)
      free_block_dict = deserializedata(dict_serialized)
      for each_block_no,each_block_file in free_block_dict.iteritems():
        free_block_count += 1
      if free_block_count > 0 & free_block_count < 10000:
        print "File system is consistent"
    except FileInUseError:
      print "Free Block FIle is corrupt or is open - Close and try Again"
    except:
      print "The free block list contains data other than the dict "
     

def validate_directory_pointers():
  for inode_no, inode_metadata_dict in filesystemmetadata['inodetable'].iteritems():
    if 'filename_to_inode_dict' in inode_metadata_dict :
      if DIRECTORYPREFIX+'.' not in val['filename_to_inode_dict'] or DIRECTORYPREFIX+'..' not in val['filename_to_inode_dict'] :
        print "Current Directory missing the ./ or ../"
      link_count = 0
      for each_filename_dir_entry in inode_metadata_dict['filename_to_inode_dict']:
        if DIRECTORYPREFIX in each_filename_dir_entry:
          link_count += 1
      if (link_count != filesystemmetadata['inodetable'][inode_no]['linkcount']):
        print "Dir has missing links or links to files which doesnt exist"        

def validate_file_indirect():
  for inode_no, inode_metadata_dict in filesystemmetadata['inodetable'].iteritems():
    if 'location' in inode_metadata_dict:
      no_of_blocks = 0
      if inode_metadata_dict['indirect'] == 1:
        curr_file_size = inode_metadata_dict['size']
        location_block_fo = openfile(FILEDATAPREFIX+str(inode_metadata_dict['location']), False) 
        temp_serialized_data = location_block_fo.readat(None,0)
        data_block_dict = deserializedata(temp_serialized_data)
        total_block_size = len(data_block_dict)* BLOCKSIZE
        if (total_block_size > curr_file_size):
          print "File Size is consistent"
    else:
        temp_fo = openfile(FILEDATAPREFIX+str(inode_metadata_dict['location']), False)
        if (len(temp_fo.readat(None,0)) != inode_metadata_dict['size']):
          print "File size is inconsistent"

def main():
  restore_metadata(metadatafilename)

if __name__ == '__main__':
    main()


