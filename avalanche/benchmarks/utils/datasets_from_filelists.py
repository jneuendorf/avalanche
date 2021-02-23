################################################################################
# Copyright (c) 2021 ContinualAI.                                              #
# Copyrights licensed under the MIT License.                                   #
# See the accompanying LICENSE file for terms.                                 #
#                                                                              #
# Date: 21-06-2020                                                             #
# Author(s): Lorenzo Pellegrini, Vincenzo Lomonaco                             #
# E-mail: contact@continualai.org                                              #
# Website: continualai.org                                                     #
################################################################################

""" This module contains useful utility functions and classes to generate
pytorch datasets based on filelists (Caffe style) """

from pathlib import Path
from typing import Tuple

import torch.utils.data as data

from PIL import Image
import os
import os.path

from avalanche.benchmarks.utils import TransformationDataset


def default_image_loader(path):
    """
    Sets the default image loader for the Pytorch Dataset.

    :param path: relative or absolute path of the file to load.

    :returns: Returns the image as a RGB PIL image.
    """
    return Image.open(path).convert('RGB')


def default_flist_reader(flist, root):
    """
    This reader reads a filelist and return a list of paths.

    :param flist: path of the flislist to read. The flist format should be:
        impath label, impath label,  ...(same to caffe's filelist)
    :param root: path to the dataset root. Each file defined in the file list
        will be searched in <root>/<impath>.

    :returns: Returns a list of paths (the examples to be loaded).
    """

    imlist = []
    with open(flist, 'r') as rf:
        for line in rf.readlines():
            impath, imlabel = line.strip().split()
            imlist.append((os.path.join(root, impath), int(imlabel)))

    return imlist


class FileDataset(data.Dataset):
    """
    This class extends the basic Pytorch Dataset class to handle list of paths
    as the main data source.
    """

    def __init__(
            self, root, files, transform=None, target_transform=None,
            loader=default_image_loader):
        """
        Creates a File Dataset from a list of files and labels.

        :param root: root path where the data to load are stored. May be None.
        :param files: list of tuples. Each tuple must contain two elements: the
            full path to the pattern and its class label.
        :param transform: eventual transformation to add to the input data (x)
        :param target_transform: eventual transformation to add to the targets
            (y)
        :param loader: loader function to use (for the real data) given path.
        """

        if root is not None:
            root = str(root)  # Manages Path objects

        self.root = root
        self.imgs = files
        self.targets = [img_data[1] for img_data in self.imgs]
        self.transform = transform
        self.target_transform = target_transform
        self.loader = loader

    def __getitem__(self, index):
        """
        Returns next element in the dataset given the current index.

        :param index: index of the data to get.
        :return: loaded item.
        """

        impath, target = self.imgs[index]
        if self.root is not None:
            impath = os.path.join(self.root, impath)
        img = self.loader(impath)
        if self.transform is not None:
            img = self.transform(img)
        if self.target_transform is not None:
            target = self.target_transform(target)

        return img, target

    def __len__(self):
        """
        Returns the total number of elements in the dataset.

        :return: Total number of dataset items.
        """

        return len(self.imgs)


class FilelistDataset(FileDataset):
    """
    This class extends the basic Pytorch Dataset class to handle filelists as
    main data source.
    """

    def __init__(
            self, root, flist, transform=None, target_transform=None,
            flist_reader=default_flist_reader, loader=default_image_loader):
        """
        This reader reads a filelist and return a list of paths.

        :param root: root path where the data to load are stored. May be None.
        :param flist: path of the flislist to read. The flist format should be:
            impath label\nimpath label\n ...(same to caffe's filelist).
        :param transform: eventual transformation to add to the input data (x).
        :param target_transform: eventual transformation to add to the targets
            (y).
        :param flist_reader: loader function to use (for the filelists) given
            path.
        :param loader: loader function to use (for the real data) given path.
        """

        flist = str(flist)  # Manages Path objects
        files_and_labels = flist_reader(flist, root)
        super().__init__(root, files_and_labels, transform=transform,
                         target_transform=target_transform, loader=loader)


def datasets_from_filelists(root, train_filelists, test_filelists,
                            complete_test_set_only=False,
                            train_transform=None, train_target_transform=None,
                            test_transform=None, test_target_transform=None):
    """
    This reader reads a list of Caffe-style filelists and returns the proper
    Dataset objects.

    A Caffe-style list is just a text file where, for each line, two elements
    are described: the path to the pattern (relative to the root parameter)
    and its class label. Those two elements are separated by a single white
    space.

    This method reads each file list and returns a separate
    dataset for each of them.

    Beware that the parameters must be **list of paths to Caffe-style
    filelists**. If you need to create a dataset given a list of
    **pattern paths**, use `datasets_from_list_of_files` instead.

    :param root: root path where the data to load are stored. May be None.
    :param train_filelists: list of paths to train filelists. The flist format
        should be: impath label\\nimpath label\\n ...(same to Caffe's filelist).
    :param test_filelists: list of paths to test filelists. It can be also a
        single path when the datasets is the same for each batch.
    :param complete_test_set_only: if True, test_filelists must contain
        the path to a single filelist that will serve as the complete test set.
        Alternatively, test_filelists can be the path (str) to the complete test
        set filelist. If False, train_filelists and test_filelists must contain
        the same amount of filelists paths. Defaults to False.
    :param train_transform: The transformation to apply to training patterns.
        Defaults to None.
    :param train_target_transform: The transformation to apply to training
        patterns targets. Defaults to None.
    :param test_transform: The transformation to apply to test patterns.
        Defaults to None.
    :param test_target_transform: The transformation to apply to test
        patterns targets. Defaults to None.

    :return: list of tuples (train dataset, test dataset) for each train
        filelist in the list.
    """

    if complete_test_set_only:
        if not (isinstance(test_filelists, str) or
                isinstance(test_filelists, Path)):
            if len(test_filelists) > 1:
                raise ValueError(
                    'When complete_test_set_only is True, test_filelists must '
                    'be a str, Path or a list with a single element describing '
                    'the path to the complete test set.')
            else:
                test_filelists = test_filelists[0]
        else:
            test_filelists = [test_filelists]
    else:
        if len(test_filelists) != len(train_filelists):
            raise ValueError(
                'When complete_test_set_only is False, test_filelists and '
                'train_filelists must contain the same number of elements.')

    transform_groups = dict(train=(train_transform, train_target_transform),
                            test=(test_transform, test_target_transform))
    train_inc_datasets = \
        [TransformationDataset(FilelistDataset(root, tr_flist),
                               transform_groups=transform_groups,
                               initial_transform_group='train')
         for tr_flist in train_filelists]
    test_inc_datasets = \
        [TransformationDataset(FilelistDataset(root, te_flist),
                               transform_groups=transform_groups,
                               initial_transform_group='test')
         for te_flist in test_filelists]

    return train_inc_datasets, test_inc_datasets


def datasets_from_list_of_files(
        train_list, test_list, complete_test_set_only=False,
        train_transform=None, train_target_transform=None,
        test_transform=None, test_target_transform=None):
    """
    This utility takes, for each dataset to generate, a list of tuples each
    containing two elements: the full path to the pattern and its class label.

    This is equivalent to `datasets_from_filelists`, which description
    contains more details on the behaviour of this utility. The two utilities
    differ in which `datasets_from_filelists` accepts paths to Caffe-style
    filelists while this one is able to create the datasets from an in-memory
    list.

    Note: this utility may try to detect (and strip) the common root path of
    all patterns in order to save some RAM memory

    :param train_list: list of lists. Each list must contain tuples of two
        elements: the full path to the pattern and its class label.
    :param test_list: list of lists. Each list must contain tuples of two
        elements: the full path to the pattern and its class label. It can be
        also a single list when the test dataset is the same for each step.
    :param complete_test_set_only: if True, test_list must contain a single list
        that will serve as the complete test set. If False, train_list and
        test_list must describe the same amount of datasets. Defaults to False.
    :param train_transform: The transformation to apply to training patterns.
        Defaults to None.
    :param train_target_transform: The transformation to apply to training
        patterns targets. Defaults to None.
    :param test_transform: The transformation to apply to test patterns.
        Defaults to None.
    :param test_target_transform: The transformation to apply to test
        patterns targets. Defaults to None.

    :return: A list of tuples (train dataset, test dataset).
    """

    if complete_test_set_only:
        # Check if the single dataset was passed as [Tuple1, Tuple2, ...]
        # or as [[Tuple1, Tuple2, ...]]
        if not isinstance(test_list[0], Tuple):
            if len(test_list) > 1:
                raise ValueError(
                    'When complete_test_set_only is True, test_list must '
                    'be a single list of tuples or a nested list containing '
                    'a single lis of tuples')
            else:
                test_list = test_list[0]
        else:
            test_list = [test_list]
    else:
        if len(test_list) != len(train_list):
            raise ValueError(
                'When complete_test_set_only is False, test_list and '
                'train_list must contain the same number of elements.')

    transform_groups = dict(train=(train_transform, train_target_transform),
                            test=(test_transform, test_target_transform))

    common_root = None

    # Detect common root
    try:
        all_paths = [pattern_tuple[0] for step_list in train_list
                     for pattern_tuple in step_list] + \
                    [pattern_tuple[0] for step_list in test_list
                     for pattern_tuple in step_list]

        common_root = os.path.commonpath(all_paths)
    except ValueError:
        # commonpath may throw a ValueError in different situations!
        # See the official documentation for more details
        pass

    if common_root is not None and len(common_root) > 0 and \
            common_root != '/':
        has_common_root = True
        common_root = str(common_root)
    else:
        has_common_root = False
        common_root = None

    if has_common_root:
        # print(f'Common root found: {common_root}!')
        # All paths have a common filesystem root
        # Remove it from all paths!
        tr_list = list()
        te_list = list()

        for idx_step_list in range(len(train_list)):
            st_list = list()
            for x in train_list[idx_step_list]:
                st_list.append((os.path.relpath(x[0], common_root), x[1]))
            tr_list.append(st_list)
        train_list = tr_list

        for idx_step_list in range(len(test_list)):
            st_list = list()
            for x in test_list[idx_step_list]:
                st_list.append((os.path.relpath(x[0], common_root), x[1]))
            te_list.append(st_list)
        test_list = te_list

    train_inc_datasets = \
        [TransformationDataset(FileDataset(common_root, tr_flist),
                               transform_groups=transform_groups,
                               initial_transform_group='train')
         for tr_flist in train_list]
    test_inc_datasets = \
        [TransformationDataset(FileDataset(common_root, te_flist),
                               transform_groups=transform_groups,
                               initial_transform_group='test')
         for te_flist in test_list]

    return train_inc_datasets, test_inc_datasets


__all__ = [
    'default_image_loader',
    'default_flist_reader',
    'FileDataset',
    'FilelistDataset',
    'datasets_from_filelists',
    'datasets_from_list_of_files'
]
