import os
from enum import Enum

import tensorflow as tf
import tensorflow_datasets.public_api as tfds

_URL = "http://cs231n.stanford.edu/tiny-imagenet-200.zip"
_EXTRACTED_FOLDER_NAME = "tiny-imagenet-200"
_LABELS_FNAME = "tiny_imagenet/tiny_imagenet_labels.txt"

SUPPORTED_IMAGE_FORMAT = (".jpg", ".jpeg", ".png")


def _list_folders(root_dir):
    return [
        f for f in tf.io.gfile.listdir(root_dir)
        if tf.io.gfile.isdir(os.path.join(root_dir, f))
    ]


def _list_imgs(root_dir):
    return [
        os.path.join(root_dir, f)
        for f in tf.io.gfile.listdir(root_dir)
        if any(f.lower().endswith(ext) for ext in SUPPORTED_IMAGE_FORMAT)
    ]


class TinyImagenetDataset(tfds.core.GeneratorBasedBuilder):
    """ tiny-imagenet dataset """
    VERSION = tfds.core.Version('0.2.0')

    def _info(self):
        names_file = tfds.core.tfds_path(_LABELS_FNAME)
        return tfds.core.DatasetInfo(
            builder=self,
            description=("""Tiny ImageNet Challenge is a similar challenge as ImageNet with a smaller dataset but
                         less image classes. It contains 200 image classes, a training
                         dataset of 100, 000 images, a validation dataset of 10, 000
                         images, and a test dataset of 10, 000 images. All images are
                         of size 64×64."""),
            features=tfds.features.FeaturesDict({
                "image": tfds.features.Image(shape=(64, 64, 3), encoding_format="jpeg"),
                "id": tfds.features.Text(),
                "label": tfds.features.ClassLabel(
                    num_classes=200,
                    names_file=names_file
                ),
                "metadata": {
                    "label_name": tf.string
                }
            }),
            supervised_keys=("image", "label"),
            citation=r"""@article{tiny-imagenet,
                              author = {Li,Fei-Fei}, {Karpathy,Andrej} and {Johnson,Justin}"}""",
        )

    def _process_train_ds(self, ds_folder, identities):
        path_to_ds = os.path.join(ds_folder, 'train')
        names = _list_folders(path_to_ds)
        
        # Read the labels file (words.txt)
        with tf.io.gfile.GFile(os.path.join(ds_folder, "words.txt")) as f:
            words_raw = f.read()

        label_names = dict(line.split("\t") for line in words_raw.split("\n"))

        label_images = {}
        for n in names:
            images_dir = os.path.join(path_to_ds, n, 'images')
            total_images = _list_imgs(images_dir)
            label_images[n] = {
                'images': total_images,
                'id': identities.index(n),
                'name': label_names[n]
            }

        return label_images

    def _process_val_ds(self, ds_folder, identities):
        path_to_ds = os.path.join(ds_folder, 'val')
        
        # Read the labels file (words.txt)
        with tf.io.gfile.GFile(os.path.join(ds_folder, "words.txt")) as f:
            words_raw = f.read()

        label_names = dict(line.split("\t") for line in words_raw.split("\n"))
        
        # read the val_annotations.txt file
        with tf.io.gfile.GFile(os.path.join(path_to_ds, 'val_annotations.txt')) as f:
            val_annotations_raw = f.read()

        label_images = {}
        for line in val_annotations_raw.split("\n"):
            if line == '':
                continue
            row_values = line.strip().split()
            label_id = row_values[1]
            if not label_id in label_images.keys():
                label_images[label_id] = {
                    'images': [],
                    'id': identities.index(label_id),
                    'name': label_names[label_id]
                }

            label_images[label_id]['images'].append(
                os.path.join(path_to_ds, 'images', row_values[0]))

        return label_images
        
    
    def _split_generators(self, dl_manager):
        extracted_path = dl_manager.extract(dl_manager.download(_URL))

        ds_folder = os.path.join(extracted_path, _EXTRACTED_FOLDER_NAME)

        with tf.io.gfile.GFile(os.path.join(ds_folder, 'wnids.txt')) as f:
            data_raw = f.read()

        lines = data_raw.split("\n")

        train_label_images = self._process_train_ds(ds_folder, lines)
        validation_label_images = self._process_val_ds(ds_folder, lines)

        return [
            tfds.core.SplitGenerator(
                name=tfds.Split.TRAIN,
                
                gen_kwargs=dict(label_images=train_label_images,)),

            tfds.core.SplitGenerator(
                name=tfds.Split.VALIDATION,
            
                gen_kwargs=dict(label_images=validation_label_images,)),
        ]

    def _generate_examples(self, label_images):
        for label, image_info in label_images.items():
            for image_path in image_info['images']:
                key = "%s/%s" % (label, os.path.basename(image_path))
                yield key, {
                    "image": image_path,
                    "id": label,
                    "label": image_info['id'],
                    "metadata": {
                        "label_name": image_info['name']
                    }
                }
