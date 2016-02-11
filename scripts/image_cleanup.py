import arrow
import ctime
import glob
import os

# article images are stored on file system.  Items expire from DB after 30 days
#   clean up articles after 31

# NOTE: ctime is last modification time, not creation time, could cause problems

img_files = glob.glob('/home/ubuntu/images/')

for img in img_files:
    time_modified = os.path.getctime(img)
    if arrow.utcnow().timestamp - time_modified > 2678400: # 31 days
        os.remove(img)
