import os
import torch
import numpy as np
import torch.utils.data as data
from .io import IO
from numpy.random import randint

class ShapeNet55Dataset(data.Dataset):
    def __init__(self, config, root, npoints, split, transform=None):
        self.data_root = os.path.join(root, 'ShapeNet-55')
        self.pc_path = os.path.join(root, 'shapenet_pc')
        self.subset = split
        self.npoints = npoints
        self.config = config
        
        self.data_list_file = os.path.join(self.data_root, f'{self.subset}.txt')
        test_data_list_file = os.path.join(self.data_root, 'test.txt')
        
        self.sample_points_num = config.npoints
        
        with open(self.data_list_file, 'r') as f:
            lines = f.readlines()
        
        self.file_list = []
        for line in lines:
            line = line.strip()
            taxonomy_id = line.split('-')[0]
            model_id = line.split('-')[1].split('.')[0]
            self.file_list.append({
                'taxonomy_id': taxonomy_id,
                'model_id': model_id,
                'file_path': line
            })
       
        self.permutation = np.arange(self.npoints)

    def pc_norm(self, pc):
        """ pc: NxC, return NxC """
        centroid = np.mean(pc, axis=0)
        pc = pc - centroid
        m = np.max(np.sqrt(np.sum(pc**2, axis=1)))
        pc = pc / m
        return pc
        

    def random_sample(self, pc, num):
        np.random.shuffle(self.permutation)
        pc = pc[self.permutation[:num]]
        return pc
    
    def make_holes_pcd(self,pcd, hole_size=0.1):
        """[summary]
    
        Arguments:
            pcd {[float[n,3]]} -- [point cloud data of n size in x, y, z format]
    
        Returns:
            [float[m,3]] -- [point cloud data in x, y, z of m size format (m < n)]
        """
        rand_point = pcd[randint(0, pcd.shape[0])]

        partial_pcd = []
    
        for i in range(pcd.shape[0]):
            dist = np.linalg.norm(rand_point - pcd[i])  
            if dist >= hole_size:
                # pcd.vertices[i] = rand_point
                partial_pcd = partial_pcd + [pcd[i]]
        return np.array([np.array(e) for e in partial_pcd])
    
    def resample_pcd(self, pcd, n):
        """Drop or duplicate points so that pcd has exactly n points"""
        idx = np.random.permutation(pcd.shape[0])
        if idx.shape[0] < n:
            idx = np.concatenate([idx, np.random.randint(pcd.shape[0], size = n - pcd.shape[0])])
        return pcd[idx[:n]]

    def __getitem__(self, idx):
        sample = self.file_list[idx]

        data = IO.get(os.path.join(self.pc_path, sample['file_path'])).astype(np.float32)

        data = self.random_sample(data, self.sample_points_num)
        data = self.pc_norm(data)

        data1 = self.resample_pcd(self.make_holes_pcd(data, hole_size=self.config.dataset.hole_size),self.sample_points_num)
        data2 = self.resample_pcd(self.make_holes_pcd(data, hole_size=self.config.dataset.hole_size),self.sample_points_num)

        data1 = torch.from_numpy(data1).float()
        data2 = torch.from_numpy(data2).float()
        return sample['taxonomy_id'], sample['model_id'], data1, data2, data

    def __len__(self):
        return len(self.file_list)