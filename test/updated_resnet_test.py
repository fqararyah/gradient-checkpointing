"""Resnet test that uses new API.

Expected result

Calling memsaving gradients with  collection
Memory used: 700.98 MB
Running without checkpoints
Memory used: 1236.68 MB
"""

USE_MINE = True  # change to False to use Tim's version

import os
os.environ['TF_CUDNN_USE_AUTOTUNE']='0'  # autotune adds random memory spikes

import math
import numpy as np
import os
import sys
import tensorflow as tf
import tensorflow.contrib.graph_editor as ge
import time


if USE_MINE:  # add folder containing memory_util.py
  #  sys.path.extend([os.environ["HOME"]+"/d/git0/pixel-cnn-private/pixel_cnn_pp"])
  sys.path.extend([".."])
  #  assert os.getcwd().endswith("tests"), "must run from tests directory"
  import memory_saving_gradients
else: # use tim's version, add folder containing "utils"
  sys.path.extend([os.environ["HOME"]+"/d/git1/pixel-cnn-private"])
  import utils.memory_saving_gradients as memory_saving_gradients

import resnet_model   

# resnet parameters
HEIGHT = 32
WIDTH = 32
DEPTH = 3
NUM_CLASSES = 10
BATCH_SIZE=128
_WEIGHT_DECAY = 2e-4
_INITIAL_LEARNING_RATE = 0.1 * BATCH_SIZE / 128
_MOMENTUM = 0.9
RESNET_SIZE=122

def create_session():
  optimizer_options = tf.OptimizerOptions(opt_level=tf.OptimizerOptions.L0)
  config = tf.ConfigProto(operation_timeout_in_ms=150000, graph_options=tf.GraphOptions(optimizer_options=optimizer_options))
  return tf.Session(config=config)

def create_loss():
  """Creates loss tensor for resnet model."""
  images = tf.random_uniform((BATCH_SIZE, HEIGHT, WIDTH, DEPTH))
  labels = tf.random_uniform((BATCH_SIZE, NUM_CLASSES))
  network = resnet_model.cifar10_resnet_v2_generator(RESNET_SIZE, NUM_CLASSES)
  inputs = tf.reshape(images, [BATCH_SIZE, HEIGHT, WIDTH, DEPTH])
  logits = network(inputs,True)
  cross_entropy = tf.losses.softmax_cross_entropy(logits=logits,
                                                  onehot_labels=labels)
  l2_penalty = tf.add_n([tf.nn.l2_loss(v) for v in tf.trainable_variables()])
  loss = cross_entropy + _WEIGHT_DECAY * l2_penalty
  return loss


def gradient_memory_test():
  """Evaluates gradient, prints peak memory."""
  loss = create_loss()

  # use block_layer1, block_layer2, block_layer3 as remember nodes
  g = tf.get_default_graph()
  ops = g.get_operations()
  for op in ge.filter_ops_from_regex(ops, "block_layer"):
    tf.add_to_collection("remember", op.outputs[0])

  grads = tf.gradients(loss, tf.trainable_variables())
  
  sess = create_session()
  sess.run(tf.global_variables_initializer())
  sess.run(grads)

  mem_op = tf.contrib.memory_stats.MaxBytesInUse()
  print("Memory used: %.2f MB "%(sess.run(mem_op)/1e6))


if __name__=='__main__':
  assert tf.test.is_gpu_available(), "Memory tracking only works on GPU"

  # replace tf.gradients with custom version
  old_gradients = tf.gradients
  def gradients_collection(ys, xs, grad_ys=None, **kwargs):
    return memory_saving_gradients.gradients(ys, xs, grad_ys,
                                             remember='collection', **kwargs)
  tf.__dict__["gradients"] = gradients_collection
  print("Running with checkpoints")
  gradient_memory_test()

  # restore old gradients
  tf.__dict__["gradients"] = old_gradients
  
  print("Running without checkpoints")
  gradient_memory_test()
