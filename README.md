# Fuse-BlockFileSystem-CS6233-OperatingSystem-I
Description: A very basic file system which can be mounted using fuse in linux using REPY.
This is done as a part of my project for the Operating Systems Course under Daniel Katz during my 1st semester.

***Note: My code can be found under: ./test-fuse/lind_fs_calls.py (The block File System)
                                   : /test-fuse/File_system_checker.py (The File System Checker)
                                  
***Important Note: If you have come across this project as a part of your OWN course work I recommend you not to COPY
the code. Its not worth to be caught under plagarism. You are paying to do this course.

You have queries in the code or understanding any parts of it, feel free to mail @ nc.vamsi@gmail.com.

*****
The description of the project given to me is as follows from the docs:

Assignment: Provide the code for a very basic file system which can be mounted using fuse in linux.  Use REPY to simplify the problem.  The file system does not need to be large, but should simulate the problems related to working with block devices.  We must support directories and files of various sizes up to a reasonable size.
Limitations: Which the file system will not be used extensively, it should be able to support, at least, a few different files with varying sizes.  Assume the following limits on the file system, however these may change in the future:

Maximum number of blocks --- 10,000
Maximum file size        --- 1,638,400 bytes
Block size               --- 4096 bytes

Prior assumptions:  You must have access to a Linux machine.  You do not need root access to the system and I would recommend that you have this in a VM so that it is easier to access and restart.  Use virtualbox and install Ubuntu 14.04LTS for this.
Step 1)

Refer to this website: https://seattle.poly.edu/wiki/Lind-fuse
The Seattle project website has loaded all of the material you need to begin creating your own file system in Linux.  Follow the directions on that page and make sure that you can mount Prof. Cappos’ file system successfully.

Step 2)

The logical layout of our file system will differ from Prof. Cappos’ considerably.  His file system stores the entire contents of a file in a single file on the “host” file system.  Since we are trying to simulate a block device, that will not work as the maximum file size could be larger than a single block.
Our layout will consist of a given number of blocks, each existing as a single file on the “host” file system with the name “linddata.X” where X is a numeric value from zero to one less than the maximum number of blocks.  Each block is preallocated (upon filesystem creation) with all zeros and stored on the host file system.
Since we will need to store more than just the files, we will use block (file) zero as the “super” block.  The super block will contain any information we wish to make persistent about the file system including its creation time, number of times it was mounted, the device_id (always 20), the location of the start and end of the free block list, the location of the root directory block and the maximum blocks in the system.  The super block will look like the following:
superBlock = {'creationTime': 1376483073,   ‘mounted’: 50, 'devId':20, ‘freeStart’:1, ‘freeEnd’:25, ‘root’:26, ‘maxBlocks’:10000}
Start by either modifying Prof Cappos’ lind_fs_calls.py or the blank template provided so that on initial mounting, the blank file system is created.  The function that Prof. Cappos uses to create his file system is “_blank_fs_init().”  In each free block, you should store the blocks which are available for data/inode storage.  You may assume that this is an array of numbers indicating the available blocks.  Since we have a limited storage in each block, you should evenly distribute the list of free block among all of the available blocks in the free block list.  For example, block 1 (the first in the free block list) would, initially, contain an array of the numeric values (pointers) of 374 blocks starting from 27 and continuing.  Block 2 would contain an array of 400 blocks starting from 401 and continuing to 799.  Yes, this means that we must aggregate the 25 blocks to find all the free blocks, but that’s not unusual for a block device.

Step 3)
Since we are simulating a real block device here, we need to store directory information for each directory.  The directory will fit into one block (in a real block device we would consider the possibility that the directory exceeded the block size, but let’s not add too much complexity).  We can trust that each directory will have the following format:
{'size':1033, 'uid':1000, 'gid':1000, 'mode':16877, 'atime':1323630836, 'ctime':1323630836, 'mtime':1323630836, 'linkcount':4, 'filename_to_inode_dict':  {'ffoo':1234, 'd.':102, 'd..':10, 'fbar':2245}}
The first letter of the name in the filename_to_inode_dict will indicate that it is a file “f’ directory “d” or special “s”.  This letter is NOT part of the filename, just a descriptor to tell you what type of inode to expect.

Now it’s time to create the root directory
{'size':0, 'uid':DEFAULT_UID, 'gid':DEFAULT_GID, 'mode':S_IFDIR | S_IRWXA, 'atime':1323630836, 'ctime':1323630836, 'mtime':1323630836, 'linkcount':2, 'filename_to_inode_dict': 
{‘d.’:rootDirectoryInode,’d..’:rootDirectoryInode}
Set rootDirectoryInode to the value in the superblock and write it out using the persist function.
Each time a new directory is created, you must allocate a new block (take the first available block from the free block list), store the directory information in the format, and add the new block to the parent’s filename_to_inode_dict.

Step 4)
Files need to be handled carefully in the file system.  The format for a file’s inode information will be: 
{'size':1033, 'uid':1000, 'gid':1000, 'mode':33261, 'linkcount':2, 'atime':1323630836, 'ctime':1323630836, 'mtime':1323630836, ‘indirect’:0 ‘location’:2444}
This data will be stored in the inode location referenced in the filename_to_inode_dict entry in the parent directory.  When a file is created, we must consider how large it is.  Since our file system can only handle blocks of 4096 bytes or less, we have to use a level of indirection if we want to store a file larger than that size.  Should we need to store a file of between 4097 and 1,638,400 bytes, we need to use an index block.  The index block is simply an array of pointers to other blocks.  Since we will not be handling anything larger than 1,638,400 bytes, and 400 pointers will easily fit into an index block, we need only a single level of indirection.
We will use the “indirect” field in the inode table to indicate if the “location” field is referencing file data or an index block.

Step 5)
Now adjust/write the necessary functions inside the lind_fs_calls.py file to perform all the necessary tasks for this file system. Most of the functions under “The actual system calls...” are what need to be modified.  

