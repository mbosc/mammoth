# Copyright 2020-present, Pietro Buzzega, Matteo Boschini, Angelo Porrello, Davide Abati, Simone Calderara.
# All rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from torchvision.datasets import CIFAR100
import torchvision.transforms as transforms
from backbone.ResNet18 import resnet18, lopeznet
import torch.nn.functional as F
import numpy as np
from utils.conf import base_path
from PIL import Image
from datasets.utils.validation import get_train_val
from datasets.utils.continual_dataset import ContinualDataset, store_masked_loaders
from datasets.utils.continual_dataset import get_previous_train_loader
from torchvision import datasets
from typing import Tuple
from datasets.transforms.denormalization import DeNormalize


class TCIFAR100(CIFAR100):
    def __init__(self, root, train=True, transform=None,
                 target_transform=None, download=False) -> None:
        self.root = root
        super(TCIFAR100, self).__init__(root, train, transform, target_transform, download=not self._check_integrity())


class MyCIFAR100(CIFAR100):
    """
    Overrides the CIFAR100 dataset to change the getitem function.
    """

    def __init__(self, root, train=True, transform=None,
                 target_transform=None, download=False) -> None:
        self.not_aug_transform = transforms.Compose([transforms.ToTensor()])
        self.root = root
        super(MyCIFAR100, self).__init__(root, train, transform, target_transform, not self._check_integrity())

    def __getitem__(self, index: int) -> Tuple[type(Image), int, type(Image)]:
        """
        Gets the requested element from the dataset.
        :param index: index of the element to be returned
        :returns: tuple: (image, target) where target is index of the target class.
        """
        img, target = self.data[index], self.targets[index]

        # to return a PIL Image
        img = Image.fromarray(img, mode='RGB')
        original_img = img.copy()

        not_aug_img = self.not_aug_transform(original_img)

        if self.transform is not None:
            img = self.transform(img)

        if self.target_transform is not None:
            target = self.target_transform(target)

        if hasattr(self, 'logits'):
            return img, target, not_aug_img, self.logits[index]

        return img, target, not_aug_img


class SequentialCIFAR100_10x10(ContinualDataset):
    NAME = 'seq-cifar100-10x10'
    DATASET_NAME = 'CIFAR100'
    SETTING = 'class-il'
    N_CLASSES_PER_TASK = 10
    N_TASKS = 10
    TRANSFORM = transforms.Compose(
        [transforms.RandomCrop(32, padding=4),
         transforms.RandomHorizontalFlip(),
         transforms.ToTensor(),
         transforms.Normalize((0.5071, 0.4867, 0.4408),
                              (0.2675, 0.2565, 0.2761))])

    def get_examples_number(self):
        train_dataset = MyCIFAR100(base_path() + self.DATASET_NAME, train=True,
                                   download=True)
        return len(train_dataset.data)

    def get_data_loaders(self):
        transform = self.TRANSFORM

        test_transform = transforms.Compose(
            [transforms.ToTensor(), self.get_normalization_transform()])

        train_dataset = MyCIFAR100(base_path() + self.DATASET_NAME, train=True,
                                   download=True, transform=transform)
        if self.args.validation:
            train_dataset, test_dataset = get_train_val(train_dataset,
                                                        test_transform, self.NAME)
        else:
            test_dataset = TCIFAR100(base_path() + self.DATASET_NAME, train=False,
                                     download=True, transform=test_transform)

        class_order = None

        #     class_order = np.array([87,  0, 52, 58, 44, 91, 68, 97, 51, 15, 94, 92, 10, 72, 49, 78, 61,
        #    14,  8, 86, 84, 96, 18, 24, 32, 45, 88, 11,  4, 67, 69, 66, 77, 47,
        #    79, 93, 29, 50, 57, 83, 17, 81, 41, 12, 37, 59, 25, 20, 80, 73,  1,
        #    28,  6, 46, 62, 82, 53,  9, 31, 75, 38, 63, 33, 74, 27, 22, 36,  3,
        #    16, 21, 60, 19, 70, 90, 89, 43,  5, 42, 65, 76, 40, 30, 23, 85,  2,
        #    95, 56, 48, 71, 64, 98, 13, 99,  7, 34, 55, 54, 26, 35, 39])

        # invert second and first task
        # class_order = np.arange(100)
        # class_order[0:10] = np.arange(10,20)
        # class_order[10:20] = np.arange(0, 10)

        train, test = store_masked_loaders(train_dataset, test_dataset, self, class_order)

        return train, test

    @staticmethod
    def get_transform():
        transform = transforms.Compose(
            [transforms.ToPILImage(), SequentialCIFAR100_10x10.TRANSFORM])
        return transform

    @staticmethod
    def get_backbone(hookme=False):
        # return resnet34(SequentialCIFAR100.N_CLASSES_PER_TASK
        #                 * SequentialCIFAR100.N_TASKS)
        return resnet18(SequentialCIFAR100_10x10.N_CLASSES_PER_TASK
                        * SequentialCIFAR100_10x10.N_TASKS, hookme=hookme)

    @staticmethod
    def get_loss():
        return F.cross_entropy

    @staticmethod
    def get_normalization_transform():
        transform = transforms.Normalize((0.5071, 0.4867, 0.4408),
                                         (0.2675, 0.2565, 0.2761))
        return transform

    @staticmethod
    def get_denormalization_transform():
        transform = DeNormalize((0.5071, 0.4867, 0.4408),
                                (0.2675, 0.2565, 0.2761))
        return transform


class SequentialCIFAR100_17x5(ContinualDataset):
    NAME = 'seq-cifar100-17x5'
    DATASET_NAME = 'CIFAR100'
    SETTING = 'class-il'
    N_CLASSES_PER_TASK = 5
    N_TASKS = 17
    SELECTED_CLASS = np.arange(15, 100)
    TRANSFORM = transforms.Compose(
        [
            # transforms.RandomCrop(32, padding=4),
            transforms.ToTensor(),
            transforms.Normalize((0.5071, 0.4867, 0.4408),
                                 (0.2675, 0.2565, 0.2761))
        ])

    def get_examples_number(self):
        train_dataset = MyCIFAR100(base_path() + self.DATASET_NAME, train=True,
                                   download=True)
        return len(train_dataset.data)

    def get_data_loaders(self):
        transform = self.TRANSFORM

        test_transform = transforms.Compose(
            [transforms.ToTensor(), self.get_normalization_transform()])

        train_dataset = MyCIFAR100(base_path() + self.DATASET_NAME, train=True,
                                   download=True, transform=transform)
        if self.args.validation:
            train_dataset, test_dataset = get_train_val(train_dataset,
                                                        test_transform, self.NAME)
        else:
            test_dataset = TCIFAR100(base_path() + self.DATASET_NAME, train=False,
                                     download=True, transform=test_transform)

        class_order = []
        for x in range(len(list(set(train_dataset.targets)))):
            append_val = x - 15 if x in self.SELECTED_CLASS else -1
            class_order.append(append_val)
        class_order_arr = np.array(class_order)
        class_order_arr[class_order_arr != -1] = np.random.permutation(class_order_arr[class_order_arr != -1])

        train, test = store_masked_loaders(train_dataset, test_dataset, self,
                                           class_order_arr)

        return train, test

    def _select_classes(self, ds: datasets):
        idx = np.concatenate([(ds.targets == x)[:, None] for x in self.SELECTED_CLASS], axis=1).any(axis=1).tolist()
        ds.targets = np.array(ds.targets)[
            np.concatenate([(ds.targets == x)[:, None] for x in self.SELECTED_CLASS], axis=1).any(
                axis=1).tolist()].tolist()

        ds.data = ds.data[idx]
        return ds

    @staticmethod
    def get_backbone(hookme=False):
        return lopeznet(SequentialCIFAR100_17x5.N_CLASSES_PER_TASK
                        * SequentialCIFAR100_17x5.N_TASKS)

    @staticmethod
    def get_loss():
        return F.cross_entropy

    @staticmethod
    def get_normalization_transform():
        transform = transforms.Normalize((0.5071, 0.4867, 0.4408),
                                         (0.2675, 0.2565, 0.2761))
        return transform

    @staticmethod
    def get_denormalization_transform():
        transform = DeNormalize((0.5071, 0.4867, 0.4408),
                                (0.2675, 0.2565, 0.2761))
        return transform


class SequentialCIFAR100_3x5(ContinualDataset):
    NAME = 'seq-cifar100-3x5'
    SETTING = 'class-il'
    N_CLASSES_PER_TASK = 5
    N_TASKS = 3
    SELECTED_CLASS = np.arange(0, 15)
    TRANSFORM = transforms.Compose(
        [transforms.RandomCrop(32, padding=4),
         transforms.ToTensor(),
         transforms.Normalize((0.5071, 0.4867, 0.4408),
                              (0.2675, 0.2565, 0.2761))])

    def get_examples_number(self):
        train_dataset = MyCIFAR100(base_path() + 'CIFAR100', train=True,
                                   download=True)
        return len(train_dataset.data)

    def get_data_loaders(self):
        transform = self.TRANSFORM

        test_transform = transforms.Compose(
            [transforms.ToTensor(), self.get_normalization_transform()])

        train_dataset = MyCIFAR100(base_path() + 'CIFAR100', train=True,
                                   download=True, transform=transform)
        if self.args.validation:
            train_dataset, test_dataset = get_train_val(train_dataset,
                                                        test_transform, self.NAME)
        else:
            test_dataset = TCIFAR100(base_path() + 'CIFAR100', train=False,
                                     download=True, transform=test_transform)

        class_order = []
        for x in range(len(list(set(train_dataset.targets)))):
            append_val = x if x in self.SELECTED_CLASS else -1
            class_order.append(append_val)

        train, test = store_masked_loaders(train_dataset, test_dataset, self,
                                           np.array(class_order))

        return train, test

    def _select_classes(self, ds: datasets):
        idx = np.concatenate([(ds.targets == x)[:, None] for x in self.SELECTED_CLASS], axis=1).any(axis=1).tolist()
        ds.targets = np.array(ds.targets)[
            np.concatenate([(ds.targets == x)[:, None] for x in self.SELECTED_CLASS], axis=1).any(
                axis=1).tolist()].tolist()

        ds.data = ds.data[idx]
        return ds

    @staticmethod
    def get_transform():
        transform = transforms.Compose(
            [transforms.ToPILImage(), SequentialCIFAR100_3x5.TRANSFORM])
        return transform

    @staticmethod
    def get_backbone(hookme=False):
        return lopeznet(SequentialCIFAR100_17x5.N_CLASSES_PER_TASK
                        * SequentialCIFAR100_17x5.N_TASKS)

    @staticmethod
    def get_loss():
        return F.cross_entropy

    @staticmethod
    def get_normalization_transform():
        transform = transforms.Normalize((0.5071, 0.4867, 0.4408),
                                         (0.2675, 0.2565, 0.2761))
        return transform

    @staticmethod
    def get_denormalization_transform():
        transform = DeNormalize((0.5071, 0.4867, 0.4408),
                                (0.2675, 0.2565, 0.2761))
        return transform
