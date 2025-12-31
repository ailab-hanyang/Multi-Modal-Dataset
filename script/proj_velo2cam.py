import sys
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import os
import open3d as o3d
from tqdm import trange

DATASET_DIR = "sequences/00"
bin_path = f"{DATASET_DIR}/velodyne"
img_path = f"{DATASET_DIR}/img"
calib_path = f"{DATASET_DIR}/calib.txt"
pcd_save_path = "output/viz_3d"
projimg_save_path = "output/viz_2d/"

os.makedirs(pcd_save_path, exist_ok=True)
os.makedirs(projimg_save_path, exist_ok=True)

if __name__ == "__main__":

    ## Find all label files
    bin_files = []
    img_files = []
    for (path, dir, files) in os.walk(bin_path):
        for filename in files:
            ext = os.path.splitext(filename)[-1]
            if ext == '.bin':
                bin_files.append(path + "/" + filename)

    for (path, dir, files) in os.walk(img_path):
        for filename in files:
            ext = os.path.splitext(filename)[-1]
            if ext == '.png':
                img_files.append(path + "/" + filename)
    
    bin_files.sort()
    img_files.sort()
    
    with open(calib_path,'r') as f:
        calib = f.readlines()

    P2 = np.matrix([float(x) for x in calib[0].strip('\n').split(' ')[1:]]).reshape(3,4)
    Tr_velo_to_cam = np.matrix([float(x) for x in calib[1].strip('\n').split(' ')[1:]]).reshape(3,4)
    Tr_velo_to_cam = np.insert(Tr_velo_to_cam,3,values=[0,0,0,1],axis=0)


    for i in trange(0,len(bin_files),ncols=80):

        bin_file = bin_files[i]
        img_file = img_files[i]

        file_name = os.path.split(bin_file)[-1]
        file_prefix = os.path.splitext(file_name)[0]

        scan = np.fromfile(bin_file, dtype=np.float32).reshape((-1,4))
        points = scan[:, 0:3] # lidar xyz (front, left, up)
        velo = np.insert(points,3,1,axis=1).T       # (4,N): xyz(3d)1

        # delete point which has x<0
        velo = np.delete(velo,np.where(velo[0,:]<0),axis=1)


        cam = P2 * Tr_velo_to_cam * velo            #  (3,N): xyz(2d)
        cam = np.concatenate((cam, velo[:3,:]), axis=0) #  (6,N): xyz(2d)xyz(3d)
        cam = np.delete(cam,np.where(cam[2,:]<0)[1],axis=1)
        cam[:2] /= cam[2,:]

        plt.figure(figsize=(9,5),dpi=96,tight_layout=True)
        png = mpimg.imread(img_file)
        IMG_H,IMG_W,_ = png.shape
        plt.axis([0,IMG_W,IMG_H,0])
        plt.imshow(png)
        u_out = np.logical_or(cam[0,:]<168, cam[0,:]>1447)
        v_out = np.logical_or(cam[1,:]<400, cam[1,:]>1119)
        outlier = np.logical_or(u_out, v_out)

        cam = np.delete(cam,np.where(outlier),axis=1) # (3,N): uvz
        cam[0,:] -= 168
        cam[1,:] -= 400
        u,v,z, _,_,_ = cam

        plt.scatter([u],[v],c=[z],cmap='rainbow_r',alpha=0.5,s=3)
        plt.savefig(projimg_save_path+str(file_prefix) + '_viz.png')
        plt.close()

        xyz = cam[3:,:].T

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.asarray(xyz))

        pcd_file_path = os.path.join(pcd_save_path, file_prefix + ".pcd")

        o3d.io.write_point_cloud(pcd_file_path, pcd)
