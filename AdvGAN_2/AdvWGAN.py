#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 15 15:40:03 2019

@author: vicari
"""

import configparser
import os

# Imports
# %%
import numpy as np
import tensorflow as tf
from IPython.display import display
from ipywidgets import FloatProgress
from keras.backend.tensorflow_backend import set_session

from AdvGAN import utils, print_functions, dataset, models, losses

# Test block, will be removed
# %%
print('AdvGAN library')


# Classes
# %%


###########################
#
# Class AdvGAN
#
###########################
class AdvWGAN:

    def set_name(self, name):
        """

        :param name:
        """
        self.name = name

    def set_generator(self, gen):
        """

        :param gen:
        """
        self.generator = gen

    def set_discriminator(self, disc):
        """

        :param disc:
        """
        self.discriminator = disc

    def set_batch_size(self, bs=None, mini_batch_max=None):
        """

        :param bs:
        :param mini_batch_max:
        """
        if bs is None:
            bs = self.batch_size
        if (mini_batch_max is not None) and (mini_batch_max < bs):
            self.batch_size = bs
            self.accumulate_grd = True
            self.batch_size = mini_batch_max
            self.n_minibatches = int(bs / mini_batch_max)
        else:
            self.batch_size = bs
            self.accumulate_grd = False
            self.n_minibatches = 1

    def set_z_dim(self, z_dim):
        """

        :param z_dim:
        """
        if not isinstance(z_dim, (list, tuple, np.ndarray)):
            z_dim = [z_dim]
        self.z_dim = z_dim

    def set_loss(self, loss):
        """

        :param loss:
        """
        possible_losses = ['gp', 'lp', 'clip', 'sn', 'ct']
        if loss['name'].lower() in possible_losses:
            self.loss = loss['name'].lower()

            if loss['name'].lower() in ['gp', 'lp', 'ct']:
                self.gp_lambda = float(loss['gp_lambda'])

            if loss['name'].lower() in ['ct']:
                self.ct_lambda = float(loss['ct_lambda'])

            if loss['name'].lower() in ['clip']:
                self.clip_value = float(loss['clip_value'])
        else:
            raise Exception('the loss {} is not valid'.format(loss))

    def set_optimizer_d(self, optimizer_d):
        """

        :param optimizer_d:
        """
        if optimizer_d['name'].lower() == 'adam':

            if optimizer_d['learning_rate'] is None:
                optimizer_d['learning_rate'] = 1e-4

            if optimizer_d['beta1'] is None:
                optimizer_d['beta1'] = 0.9

            if optimizer_d['beta2'] is None:
                optimizer_d['beta2'] = 0.99

            self.optimizer_D = tf.compat.v1.train.AdamOptimizer(learning_rate=float(optimizer_d['learning_rate']),
                                                                beta1=float(optimizer_d['beta1']),
                                                                beta2=float(optimizer_d['beta2']))

        elif optimizer_d['name'].lower() == 'rmsprop':

            if optimizer_d['learning_rate'] is None:
                optimizer_d['learning_rate'] = 1e-4

            self.optimizer_D = tf.compat.v1.train.RMSPropOptimizer(learning_rate=float(optimizer_d['learning_rate']))

        else:
            raise Exception('the optimizer {} is not valid'.format(optimizer_d['name']))

    def set_optimizer_g(self, optimizer_g):
        """

        :param optimizer_g:
        """
        if optimizer_g['name'].lower() == 'adam':

            if optimizer_g['learning_rate'] is None:
                optimizer_g['learning_rate'] = 1e-4

            if optimizer_g['beta1'] is None:
                optimizer_g['beta1'] = 0.9

            if optimizer_g['beta2'] is None:
                optimizer_g['beta2'] = 0.99

            self.optimizer_G = tf.compat.v1.train.AdamOptimizer(learning_rate=float(optimizer_g['learning_rate']),
                                                                beta1=float(optimizer_g['beta1']),
                                                                beta2=float(optimizer_g['beta2']))

        elif optimizer_g['name'].lower() == 'rmsprop':

            if optimizer_g['learning_rate'] is None:
                optimizer_g['learning_rate'] = 1e-4

            self.optimizer_G = tf.compat.v1.train.RMSPropOptimizer(learning_rate=float(optimizer_g['learning_rate']))

        else:
            raise Exception('the optimizer {} is not valid'.format(optimizer_g['name']))

    def set_dataset(self, data):
        """

        :param data:
        """
        if not isinstance(data, dataset.Dataset):
            raise Exception('the dataset must be a Dataset object')
        else:
            self.data = data

    def set_training_options(self, nb_iter=None, init_step=None, n_c_iters_start=None, n_c_iters=None,
                             g_iter_start=None, g_iter=None):
        """

        :param nb_iter:
        :param init_step:
        :param n_c_iters_start:
        :param n_c_iters:
        :param g_iter_start:
        :param g_iter:
        """
        if init_step is not None:
            self.init_step = init_step

        if n_c_iters_start is not None:
            self.n_c_iters_start = n_c_iters_start

        if n_c_iters is not None:
            self.n_c_iters = n_c_iters

        if nb_iter is not None:
            self.nb_iter = nb_iter

        if g_iter_start is not None:
            self.g_iter_start = g_iter_start

        if g_iter is not None:
            self.g_iter = g_iter

    def set_classifier(self, classifier=None, nb_class=None):
        """

        :param classifier:
        :param nb_class:
        """
        if classifier is not None:
            self.classifier = classifier

        if nb_class is not None:
            self.nb_class = nb_class

    def set_logs(self, print_method=None, frequency_print=None, frequency_logs=None, logs_path=None):
        """

        :param print_method:
        :param frequency_print:
        :param frequency_logs:
        :param logs_path:
        """
        if print_method is not None:
            self.print_method = print_method

        if frequency_print is not None:
            self.frequency_print = frequency_print

        if frequency_logs is not None:
            self.frequency_logs = frequency_logs

        if logs_path is not None:
            self.logs_path = logs_path

    def set_temperature(self, temperature):
        """

        :param temperature:
        """
        self.temperature = temperature

    def set_adv(self, adv=True):
        """

        :param adv:
        """
        self.adv = adv

    def set_uses(self, use_proba=None, use_ceil=None, ceil_value=None, use_labels=None, use_mask=None,
                 use_softmax=None, use_recon=None, recon_beta=None, reg_losses=None, reg_term=None,
                 use_clf=None, label_used=None, clf_alpha=None):
        """

        :param use_proba:
        :param use_ceil:
        :param ceil_value:
        :param use_labels:
        :param use_mask:
        :param use_softmax:
        :param use_recon:
        :param recon_beta:
        :param reg_losses:
        :param reg_term:
        :param use_clf:
        :param label_used:
        :param clf_alpha:
        """
        if use_proba is not None:
            self.use_proba = use_proba
        if use_ceil is not None:
            self.use_ceil = use_ceil
        if ceil_value is not None:
            self.ceil_value = ceil_value
        if use_labels is not None:
            self.use_labels = use_labels
        if use_mask is not None:
            self.use_mask = use_mask
        if use_softmax is not None:
            self.use_softmax = use_softmax
        if recon_beta is not None:
            self.recon_beta = recon_beta
        if use_recon is not None:
            self.use_recon = use_recon
        if reg_losses is not None:
            self.reg_losses = reg_losses
        if reg_term is not None:
            self.reg_term = reg_term
        if use_clf is not None:
            self.use_clf = use_clf
        if label_used is not None:
            self.label_used = label_used
        if clf_alpha is not None:
            self.clf_alpha = clf_alpha

    def __init__(self):

        self.generator = models.make_fc(
            hiddens_dims=[64, 64, 64],
            ouput_dims=2,
            scope_name="generator",
            h=tf.nn.relu,
            o=tf.nn.tanh,
            use_sn=False,
            use_bias=True,
            default_reuse=False
        )

        self.discriminator = models.make_fc(
            hiddens_dims=[128, 128, 128],
            ouput_dims=1,
            scope_name="discriminator",
            h=lambda x: tf.nn.leaky_relu(x, 0.2),
            use_sn=False,
            use_bias=True,
            default_reuse=True
        )

        self.accumulate_grd = False
        self.n_minibatches = 1
        self.batch_size = 64
        self.name = "AdvGAN"

        self.use_adaptive_adv = False

        self.z_dim = [None]
        self.gp_lambda = 10
        self.ct_lambda = 2

        self.optimizer_D = tf.compat.v1.train.RMSPropOptimizer(learning_rate=1e-4)
        self.optimizer_G = tf.compat.v1.train.RMSPropOptimizer(learning_rate=1e-4)

        self.nb_class = 10
        self.init_step = 1
        self.n_c_iters_start = 5
        self.n_c_iters = 5
        self.g_iter_start = 1
        self.g_iter = 1
        self.nb_iter = 5000
        self.ceil_value = 0.75

        self.saver = None

        self.reg_losses = False

        self.data = None
        self.classifier = None

        self.classifier_reshape = None
        self.classifier_norm = None

        self.dataset_is_tf = False

        self.nb_classes = 10

        self.print_method = print_functions.show_it_label('advGAN')
        self.frequency_print = 100
        self.frequency_logs = None
        self.logs_path = './logs/'

        self.loss = 'lp'

        self.temperature = 20
        self.clip_value = 0.1
        self.m_value = 0.2

        self.adv = True
        self.use_proba = True
        self.use_ceil = False
        self.use_labels = False
        self.use_mask = False
        self.mask = None
        self.use_recon = False
        self.recon_beta = 1.0
        self.use_softmax = True

        self.reg_losses = False
        self.reg_term = 1e-3
        self.use_clf = False
        self.label_used = [1, 0, 0, 0, 0, 0]
        self.clf_alpha = 1.0

        self.g_loss = None
        self.d_loss = None

        self.batch_reg = False

        self.X_real = None
        self.labels = None
        self.classifier_proba = None
        self.adv_map = None
        self.z = None
        self.is_training = None
        self.pred_real = None
        self.X_fake = None
        self.pred_fake = None
        self.loss_clf = None
        self.neg_loss = None
        self.accum_vars_D = None
        self.accumulation_counter_D = None
        self.accum_vars_G = None
        self.accumulation_counter_G = None
        self.D_sum = None
        self.G_sum = None
        self.accum_ops_G = None
        self.accum_ops_D = None
        self.zero_ops_G = None
        self.zero_ops_D = None
        self.G_step = None
        self.D_step = None
        self.D_clipping = None

        self.f_prog = None
        self.critic_losses = None
        self.neg_losses = None
        self.generator_losses = None
        self.writer = None
        self.sample_labels = None

        self.built = False

    def summary(self):
        print("AdvGan Options :")

        print()
        print("accumulate_grd :", self.accumulate_grd)
        print("n_minibatches :", self.n_minibatches)
        print("batch_size :", self.batch_size)
        print("name :", self.name)

        print("use_adaptative_adv :", self.use_adaptive_adv)

        print("z_dim :", self.z_dim)
        print("gp_lambda :", self.gp_lambda)
        print("ct_lambda :", self.ct_lambda)

        print("optimizer_D :", self.optimizer_D)
        print("optimizer_G :", self.optimizer_G)

        print("init_step :", self.init_step)
        print("n_c_iters_start :", self.n_c_iters_start)
        print("n_c_iters :", self.n_c_iters)
        print("g_iter :", self.g_iter)
        print("nb_iter :", self.nb_iter)

        print("reg_losses :", self.reg_losses)

        print("frequency_print :", self.frequency_print)
        print("frequency_logs :", self.frequency_logs)
        print("logs_path :", self.logs_path)

        print("loss :", self.loss)

        print("temperature :", self.temperature)
        print("clip_value :", self.clip_value)

        print("adv :", self.adv)
        print("use_proba :", self.use_proba)
        print("use_ceil :", self.use_ceil)
        print("use_labels :", self.use_labels)
        print("use_recon :", self.use_recon)
        print("recon_beta :", self.recon_beta)
        print("use_clf :", self.use_clf)

    @staticmethod
    def noise(batch_size, z_size):
        """

        :rtype: object
        :param batch_size:
        :param z_size:
        :return:
        """
        size = [batch_size] + z_size
        rand = np.ones(len(size), dtype=np.int)
        rand[-1] = size[-1]
        rand[0] = size[0]
        ones = np.ones(size, dtype=np.float)
        return ones * np.random.normal(0., 1., size=rand)

    def build_model(self, reset_graph=False):
        """
        Function to build the graph use for AdvGAN
        :type reset_graph: bool
        """

        if self.data is None:
            raise Exception('a dataset must be specified')

        if self.adv and (self.classifier is None):
            raise Exception('A classifier must be specified to train in adversarial mode')

        if reset_graph:
            tf.compat.v1.reset_default_graph()

        self.dataset_is_tf = self.data.is_tf

        if self.adv:
            self.classifier.load_model()

        shape_x, shape_y = self.data.shape()
        number_of_samples = shape_x[0]
        shape_x[0] = None

        z_dims = [None] + self.z_dim

        shape_y[0] = None

        if self.dataset_is_tf:
            if self.use_mask:
                self.X_real, self.labels, _, self.mask = self.data.next_batch()
                probs = self.classifier.predict(self.X_real)[:, :, :, 4]
                labels_masked = tf.cast(self.labels * self.mask, tf.float32)
                pm = tf.cast(tf.expand_dims(probs, -1) * labels_masked, tf.float32)
                self.classifier_proba = tf.cast(
                    1.0 - (tf.reduce_sum(input_tensor=pm, axis=[1, 2, 3]) / tf.reduce_sum(input_tensor=labels_masked,
                                                                                          axis=[1, 2, 3])), tf.float32)
                self.mask.set_shape(shape_y)
            elif self.use_labels:
                self.X_real, self.labels, _, _ = self.data.next_batch()
                self.mask = self.labels
                probs = self.classifier.predict(self.X_real)[:, :, :, 4]
                pm = tf.cast(tf.expand_dims(probs, -1) * self.labels, tf.float32)
                self.classifier_proba = tf.cast(
                    1.0 - (tf.reduce_sum(input_tensor=pm, axis=[1, 2, 3]) / tf.reduce_sum(input_tensor=self.labels,
                                                                                          axis=[1, 2, 3])), tf.float32)
            else:
                self.X_real, self.labels, self.classifier_proba = self.data.next_batch()

            self.X_real.set_shape(shape_x)
            self.labels.set_shape(shape_y)

            if self.use_ceil and self.ceil_value is not None:
                self.classifier_proba = tf.minimum(self.classifier_proba, self.ceil_value)

            self.classifier_proba = tf.nn.softmax(self.classifier_proba * self.temperature)
            self.classifier_proba = tf.expand_dims(self.classifier_proba, -1)

        else:
            self.X_real = tf.compat.v1.placeholder("float", shape_x, name="X_real")
            self.labels = tf.compat.v1.placeholder("float", shape_y, name="labels")
            self.classifier_proba = tf.compat.v1.placeholder("float", [None, 1], name="classifier_proba")
            self.adv_map = tf.compat.v1.placeholder("float", shape_y, name="adv_map")

        self.z = tf.compat.v1.placeholder("float", z_dims, name="z_input")
        self.is_training = tf.compat.v1.placeholder(tf.bool, shape=())
        if self.use_clf:
            self.label_used = tf.constant(self.label_used, dtype='float')

        # train with real and classifier

        if self.use_labels:
            self.pred_real = self.discriminator(self.X_real, self.labels, reuse=False)
        elif self.use_mask:
            self.pred_real = self.discriminator(self.X_real, self.mask, reuse=False)
        else:
            self.pred_real = self.discriminator(self.X_real, reuse=False)

        if self.adv:
            self.pred_real *= self.classifier_proba

        if self.batch_reg:
            self.pred_real *= self.batch_size / number_of_samples

        # train with fake
        if self.use_labels:
            self.X_fake = self.generator(self.X_real, self.labels, self.z, train=self.is_training)
        elif self.use_mask:
            self.X_fake = self.generator(self.X_real, self.mask, self.z, train=self.is_training)
        else:
            self.X_fake = self.generator(self.z, train=self.is_training)

        self.X_fake = tf.identity(self.X_fake, name="X_fake")

        shape_x[0] = -1

        self.X_fake = tf.reshape(self.X_fake, shape_x)

        if self.use_labels:
            self.pred_fake = self.discriminator(self.X_fake, self.labels)
        elif self.use_mask:
            self.pred_fake = self.discriminator(self.X_fake, self.mask)
        else:
            self.pred_fake = self.discriminator(self.X_fake)

        if self.adv and not self.use_softmax:
            self.pred_fake *= 1 / number_of_samples

        self.g_loss = - tf.reduce_mean(input_tensor=self.pred_fake)

        if self.adv and not self.use_softmax:
            self.d_loss = - (tf.reduce_sum(input_tensor=self.pred_real) - tf.reduce_sum(input_tensor=self.pred_fake))
        elif self.adv:
            self.d_loss = - (tf.reduce_sum(input_tensor=self.pred_real) - tf.reduce_mean(input_tensor=self.pred_fake))
        else:
            self.d_loss = - (tf.reduce_mean(input_tensor=self.pred_real) - tf.reduce_mean(input_tensor=self.pred_fake))

        if self.reg_losses:
            self.d_loss = self.reg_term * self.d_loss
            self.g_loss = self.reg_term * self.g_loss

        if self.use_recon:
            if self.use_mask:
                x_fake_masked = (1 - self.mask) * self.X_fake
                x_real_masked = (1 - self.mask) * self.X_real
            elif self.use_labels:
                x_fake_masked = (1 - self.labels) * self.X_fake
                x_real_masked = (1 - self.labels) * self.X_real
            else:
                raise Exception('something wrong')

            self.g_loss += self.recon_beta * (tf.reduce_mean(
                input_tensor=tf.reduce_sum(input_tensor=tf.square(x_fake_masked - x_real_masked),
                                           axis=np.arange(1, len(x_fake_masked.shape)))))

        if self.use_clf:
            y_t = self.mask * self.label_used
            preds = self.classifier.predict(self.X_fake)
            preds = preds * self.mask
            preds = 1 - preds
            self.loss_clf = self.clf_alpha * tf.reduce_mean(
                input_tensor=-tf.reduce_sum(input_tensor=y_t * tf.math.log(tf.clip_by_value(preds, 1e-10, 1.0)),
                                            axis=[1]))
            self.g_loss += self.loss_clf

        self.neg_loss = - self.d_loss

        if self.use_labels:
            labels = self.labels
        elif self.use_mask:
            labels = self.mask
        else:
            labels = None

        if self.loss == 'gp':
            self.d_loss += losses.gp_loss(self.X_real, self.X_fake, self.discriminator, shape_x, labels=labels)

        if self.loss == 'lp':
            self.d_loss += losses.lp_loss(self.X_real, self.X_fake, self.discriminator, shape_x, labels=labels)

        if self.loss == 'ct':
            self.d_loss += losses.lp_loss(self.X_real, self.X_fake, self.discriminator, shape_x, labels=labels)
            self.d_loss += losses.ct_loss(self.X_real, self.discriminator, labels=labels)

        d_vars = [var for var in tf.compat.v1.trainable_variables() if "discriminator" in var.name]
        g_vars = [var for var in tf.compat.v1.trainable_variables() if "generator" in var.name]

        if self.accumulate_grd:
            # initialized with 0s

            self.accum_vars_D = [tf.Variable(tf.zeros_like(tv.initialized_value()), trainable=False) for tv in d_vars]
            self.accumulation_counter_D = tf.Variable(0.0, trainable=False)

            self.accum_vars_G = [tf.Variable(tf.zeros_like(tv.initialized_value()), trainable=False) for tv in g_vars]
            self.accumulation_counter_G = tf.Variable(0.0, trainable=False)

        self.D_sum = tf.compat.v1.summary.scalar('D_loss', self.d_loss)
        self.G_sum = tf.compat.v1.summary.scalar('G_loss', self.g_loss)

        with tf.control_dependencies(tf.compat.v1.get_collection(tf.compat.v1.GraphKeys.UPDATE_OPS)):

            if self.accumulate_grd:

                gvs_g = self.optimizer_G.compute_gradients(self.g_loss, g_vars)
                gvs_d = self.optimizer_D.compute_gradients(self.d_loss, d_vars)

                self.accum_ops_G = [accumulator.assign_add(grad) for (accumulator, (grad, var)) in
                                    zip(self.accum_vars_G, gvs_g)]
                self.accum_ops_G.append(self.accumulation_counter_G.assign_add(1.0))

                self.accum_ops_D = [accumulator.assign_add(grad) for (accumulator, (grad, var)) in
                                    zip(self.accum_vars_D, gvs_d)]
                self.accum_ops_D.append(self.accumulation_counter_D.assign_add(1.0))

                self.G_step = self.optimizer_G.apply_gradients(
                    [(accumulator / self.accumulation_counter_G, var) for (accumulator, (grad, var)) in
                     zip(self.accum_vars_G, gvs_g)])

                self.D_step = self.optimizer_D.apply_gradients(
                    [(accumulator / self.accumulation_counter_D, var) for (accumulator, (grad, var)) in
                     zip(self.accum_vars_D, gvs_d)])

                self.zero_ops_G = [accumulator.assign(tf.zeros_like(tv)) for (accumulator, tv) in
                                   zip(self.accum_vars_G, g_vars)]
                self.zero_ops_D = [accumulator.assign(tf.zeros_like(tv)) for (accumulator, tv) in
                                   zip(self.accum_vars_D, d_vars)]

                self.zero_ops_G.append(self.accumulation_counter_G.assign(0.0))
                self.zero_ops_D.append(self.accumulation_counter_D.assign(0.0))

            else:
                self.G_step = self.optimizer_G.minimize(self.g_loss, var_list=g_vars)
                self.D_step = self.optimizer_D.minimize(self.d_loss, var_list=d_vars)

            if self.loss == 'clip':
                self.D_clipping = [w.assign(tf.clip_by_value(w, -self.clip_value, self.clip_value)) for w in d_vars]

        self.saver = tf.compat.v1.train.Saver()
        self.built = True

    def train(self, init_step=None, n_c_iters_start=None, n_c_iters=None, nb_iter=None, print_method=None,
              frequency_print=None,
              frequency_logs=None, use_ceil=None, restore=False, restore_meta=False, restore_it=True,
              file_to_restore=None):
        """
        Function to train AdvGAN

        Parameters
        ----------
        """
        if not self.built:
            raise Exception('Build the model first')

        if init_step is not None:
            self.init_step = init_step
        if n_c_iters_start is not None:
            self.n_c_iters_start = n_c_iters_start
        if n_c_iters is not None:
            self.n_c_iters = n_c_iters
        if nb_iter is not None:
            self.nb_iter = nb_iter
        if print_method is not None:
            self.print_method = print_method
        if frequency_print is not None:
            self.frequency_print = frequency_print
        if frequency_logs is not None:
            self.frequency_logs = frequency_logs
        if use_ceil is not None:
            self.use_ceil = use_ceil

        self.f_prog = FloatProgress(min=0, max=self.nb_iter)
        display(self.f_prog)

        config = tf.compat.v1.ConfigProto()
        config.gpu_options.allow_growth = True
        with tf.compat.v1.Session(config=config) as sess:
            set_session(sess)
            sess.run(tf.compat.v1.global_variables_initializer())
            it = 0
            if restore:
                if file_to_restore is not None:
                    name = file_to_restore
                else:
                    name = self.name
                if restore_meta:
                    self.saver = tf.compat.v1.train.import_meta_graph("data/" + name + '.ckpt.meta')
                exists = os.path.isfile("data/" + name + '.ckpt.index')
                if exists:
                    self.saver.restore(sess, "data/" + name + '.ckpt')
                else:
                    print('no weights found, training with new weights')
                exists = os.path.isfile("data/logs.npy")
                if exists:
                    loader = np.load('data/logs.npy')
                    self.critic_losses = loader[0]
                    self.neg_losses = loader[1]
                    self.generator_losses = loader[2]
                else:
                    print('BEWARE !!!! no logs found, creating new logs')
                exists = os.path.isfile("data/" + name + '.saved')
                if exists and restore_it:
                    config = configparser.ConfigParser()
                    config.read("data/" + name + '.saved')
                    ckpt = config['ckpt']
                    it = ckpt.getint('it')
                    print("Model load at it=", it)
                    it = it + 1

            # GAN_vars = [var for var in tf.global_variables() if "GAN" in var.name]
            # sess.run(tf.variables_initializer(GAN_vars))

            self.classifier.load_weights()

            if self.adv and not self.data.is_tf:
                self.data.adv_proba(self.classifier)

            self.critic_losses = []
            self.neg_losses = []
            self.generator_losses = []
            d_sum, g_sum = None, None
            self.writer = tf.summary.FileWriter(self.logs_path, graph=tf.compat.v1.get_default_graph())

            ##################################################
            # Train phase
            ##################################################

            n_c_iters = self.n_c_iters_start
            g_iter = self.g_iter_start

            for self.it in range(it, self.nb_iter + 1):
                if self.it > self.init_step:
                    n_c_iters = self.n_c_iters
                    g_iter = self.g_iter

                # loss_critic = [] # To be sure there is convergence

                ##################################################
                # Train the discriminator
                ##################################################

                for _ in range(n_c_iters):
                    dl = []
                    nl = []
                    for _ in range(self.n_minibatches):
                        # On recupere le batch suivant
                        if self.use_labels and not self.dataset_is_tf:
                            x_mb, y, c_proba = self.data.next_batch(self.batch_size, with_labels=True, with_proba=True)
                        elif self.use_proba and not self.use_labels and not self.dataset_is_tf:
                            x_mb, c_proba = self.data.next_batch(self.batch_size, with_proba=True)
                        elif not self.dataset_is_tf:
                            x_mb = self.data.next_batch(self.batch_size)

                        # To train to genererate adversarial exemple
                        if self.adv and not self.dataset_is_tf:
                            # On recupere le p barre de la classe c
                            if self.use_proba:
                                if self.use_ceil:
                                    if self.ceil_value is not None:
                                        c_proba = utils.ceil(c_proba, self.ceil_value)
                                    else:
                                        c_proba = utils.ceiling_with_interp(c_proba, self.batch_size)

                                if self.use_softmax:
                                    c_proba = utils.softmax(c_proba, self.temperature)
                            c_proba = np.reshape(c_proba, (-1, 1))

                            if self.use_labels:
                                if self.dataset_is_tf:
                                    fd = {self.z: self.noise(self.batch_size, self.z_dim), self.is_training: True}

                                else:
                                    fd = {self.classifier_proba: c_proba, self.X_real: x_mb, self.labels: y,
                                          self.z: self.noise(self.batch_size, self.z_dim), self.is_training: True}
                            else:
                                fd = {self.classifier_proba: c_proba, self.X_real: x_mb,
                                      self.z: self.noise(self.batch_size, self.z_dim), self.is_training: True}
                        # Classic GAN
                        else:
                            if self.dataset_is_tf:
                                fd = {self.z: self.noise(self.batch_size, self.z_dim), self.is_training: True}

                            else:
                                fd = {self.X_real: x_mb, self.z: self.noise(self.batch_size, self.z_dim),
                                      self.is_training: True}

                        if self.accumulate_grd:
                            _, loss, lossn = sess.run([self.accum_ops_D, self.d_loss, self.neg_loss], feed_dict=fd)
                            dl.append(loss)
                            nl.append(lossn)

                    if self.accumulate_grd:
                        _ = sess.run(self.D_step)
                        _ = sess.run(self.zero_ops_D)

                    else:
                        _, _, d_loss, neg_loss = sess.run(
                            [self.D_step, self.D_sum, self.d_loss, self.neg_loss],
                            feed_dict=fd)

                        # If we use weight clipping
                    if self.loss == 'clip':
                        sess.run(self.D_clipping)

                ##################################################
                # Train the generator
                ##################################################
                gl = []
                for _ in range(self.n_minibatches):
                    for _ in range(g_iter):
                        if self.dataset_is_tf:
                            fd = {self.z: self.noise(self.batch_size, self.z_dim), self.is_training: True}
                        elif self.use_labels:
                            x_mb, y, c_proba = self.data.next_batch(self.batch_size, with_labels=True, with_proba=True)
                            fd = {self.z: self.noise(self.batch_size, self.z_dim), self.X_real: x_mb,
                                  self.labels: y, self.is_training: True}
                        else:
                            fd = {self.z: self.noise(self.batch_size, self.z_dim), self.is_training: True}

                        if self.accumulate_grd:
                            _, loss = sess.run([self.accum_ops_G, self.g_loss], feed_dict=fd)
                            gl.append(loss)

                    if self.accumulate_grd:
                        _ = sess.run(self.G_step)
                        _ = sess.run(self.zero_ops_G)

                    else:
                        _, g_sum, g_loss = sess.run(
                            [self.G_step, self.G_sum, self.g_loss],
                            feed_dict=fd)

                ##################################################
                # Logs
                ##################################################
                if self.accumulate_grd:
                    neg_loss = np.mean(nl)
                    d_loss = np.mean(dl)
                    g_loss = np.mean(gl)

                self.neg_losses.append(neg_loss)
                self.critic_losses.append(d_loss)

                self.generator_losses.append(g_loss)
                self.f_prog.value += 1

                if self.frequency_logs is not None:
                    if self.it % self.frequency_logs == 0:
                        self.writer.add_summary(d_sum, self.it)
                        self.writer.add_summary(g_sum, self.it)

                ##################################################
                # print_method and save
                #####
                if self.it % self.frequency_print == 0:
                    if self.print_method is not None:
                        if self.dataset_is_tf:
                            samples = self.X_fake.eval(
                                feed_dict={self.z: self.noise(self.batch_size, self.z_dim), self.is_training: False})
                        elif self.use_labels:
                            x_mb, self.sample_labels, c_proba = self.data.next_batch(self.batch_size, with_labels=True,
                                                                                     with_proba=True)
                            samples = self.X_fake.eval(feed_dict={self.X_real: x_mb, self.labels: self.sample_labels,
                                                                  self.z: self.noise(self.batch_size, self.z_dim),
                                                                  self.is_training: False})
                        else:
                            x_mb = self.data.next_batch(self.batch_size)
                            samples = self.X_fake.eval(
                                feed_dict={self.z: self.noise(self.batch_size, self.z_dim), self.is_training: False})

                        self.print_method(samples=samples, gan=self)
                    # To save the model
                    w_meta_graphe = False
                    if self.it == 0:
                        w_meta_graphe = True
                    keep = 1
                    if keep > 1:
                        self.saver.save(sess, "data/" + self.name + ".ckpt", write_meta_graph=w_meta_graphe,
                                        global_step=self.it, max_to_keep=keep)
                    else:
                        self.saver.save(sess, "data/" + self.name + ".ckpt", write_meta_graph=w_meta_graphe)

                    config = configparser.ConfigParser()
                    config['ckpt'] = {'it': str(self.it)}
                    with open("data/" + self.name + ".saved", 'w') as cfg:
                        config.write(cfg)
                    np.save('data/logs.npy', [self.critic_losses, self.neg_losses, self.generator_losses])

    #############################################
    #############################################

    def generate(self, batch_size=None):
        """
        Function to generate a batch of data

        Parameters
        ----------
        batch_size: int
            number of data generated, use the set value by default, optional

        Returns
        -------
        array
            batch of generated data
        """
        nb = self.batch_size
        if batch_size is not None:
            nb = batch_size
        with tf.compat.v1.Session() as sess:
            self.saver.restore(sess, "data/" + self.name + ".ckpt")
            return self.X_fake.eval(feed_dict={self.z: self.noise(nb, self.z_dim), self.is_training: False})

    #############################################

    def discriminate(self, img):
        with tf.compat.v1.Session() as sess:
            self.saver.restore(sess, "data/" + self.name + ".ckpt")
            return self.pred_fake.eval(feed_dict={self.X_fake: img})

            #############################################

    def generate_with_noise(self, noise):
        """
        Function to generate a batch of data

        Parameters
        ----------
        noise: array of shape [batch, z_dim]
            The noise for the generator

        Returns
        -------
        array
            batch of generated data
        """
        with tf.compat.v1.Session() as sess:
            self.saver.restore(sess, "data/" + self.name + ".ckpt")
            return self.X_fake.eval(feed_dict={self.z: noise, self.is_training: False})

    #############################################

    def load_and_generate(self, path, noise=None, batch_size=None, data=None, restore_meta=False):
        """

        :param path:
        :param noise:
        :param batch_size:
        :param data:
        :param restore_meta:
        :return:
        """
        nb = self.batch_size
        with tf.compat.v1.Session() as sess:
            if restore_meta:
                self.saver = tf.compat.v1.train.import_meta_graph("data/" + path + '.ckpt.meta')
            self.saver.restore(sess, "data/" + path + ".ckpt")
            if batch_size is not None:
                nb = batch_size
            if noise is None:
                noise = self.noise(nb, self.z_dim)
            if self.use_labels:
                if data is None:
                    if self.dataset_is_tf:
                        return sess.run([self.X_fake, self.X_real, self.labels, self.classifier_proba],
                                        feed_dict={self.z: self.noise(self.batch_size, self.z_dim),
                                                   self.is_training: False})
                    else:
                        x_mb, sample_labels, c_proba = self.data.next_batch(nb)
                        return self.X_fake.eval(feed_dict={self.X_real: x_mb, self.labels: sample_labels, self.z: noise,
                                                           self.is_training: False}), x_mb, sample_labels
                else:
                    return self.X_fake.eval(
                        feed_dict={self.X_real: data[0], self.labels: data[1], self.z: noise, self.is_training: False})

            else:
                if data is None:
                    if self.dataset_is_tf:
                        return sess.run([self.X_fake, self.X_real, self.labels, self.classifier_proba],
                                        feed_dict={self.z: self.noise(self.batch_size, self.z_dim),
                                                   self.is_training: False})
                    else:
                        return self.X_fake.eval(feed_dict={self.z: noise, self.is_training: False})
                else:
                    return self.X_fake.eval(feed_dict={self.X_real: data, self.z: noise, self.is_training: False})

    def load_and_generate_mask(self, path, noise=None, batch_size=None, data=None, mask=None, restore_meta=False):
        """

        :param path:
        :param noise:
        :param batch_size:
        :param data:
        :param mask:
        :param restore_meta:
        :return:
        """
        nb = self.batch_size
        with tf.compat.v1.Session() as sess:
            if restore_meta:
                self.saver = tf.compat.v1.train.import_meta_graph("data/" + path + '.ckpt.meta')
            self.saver.restore(sess, "data/" + path + ".ckpt")
            if batch_size is not None:
                nb = batch_size
            if noise is None:
                noise = self.noise(nb, self.z_dim)
            if data is None:
                if self.dataset_is_tf:
                    return sess.run([self.X_fake, self.X_real, self.labels, self.classifier_proba],
                                    feed_dict={self.z: self.noise(self.batch_size, self.z_dim),
                                               self.is_training: False})
                else:
                    return self.X_fake.eval(feed_dict={self.z: noise, self.is_training: False})
            else:
                return self.X_fake.eval(
                    feed_dict={self.X_real: data, self.mask: mask, self.z: noise, self.is_training: False})

    #############################################

    def load_and_discriminate(self, path, data):
        with tf.compat.v1.Session() as sess:
            self.saver.restore(sess, "data/" + path + ".ckpt")
            return self.pred_fake.eval(feed_dict={self.X_fake: data})

    #############################################

    def save_loss(self, path='./loss'):
        """
        Function to save the critic loss
        """
        np.save(path, self.critic_losses)


##########################################################################################
##########################################################################################
##########################################################################################


def make_gan(file):
    config = configparser.ConfigParser()
    config.read(file)

    adv_gan = AdvWGAN()

    # MISC
    misc = config['MISC']

    adv_gan.set_name(misc.get('name'))
    adv_gan.set_adv(misc.getboolean('adv'))
    adv_gan.set_z_dim(eval(misc.get('z_dim')))
    adv_gan.set_batch_size(misc.getint('batch_size'))
    adv_gan.set_batch_size(misc.getint('mini_batch_max'))
    adv_gan.set_temperature(misc.getfloat('temperature'))

    # USES
    uses = config['USES']
    adv_gan.set_uses(uses.getboolean('use_proba'), uses.getboolean('use_ceil'), uses.getfloat('ceil_value'),
                     uses.getboolean('use_labels'), uses.getboolean('use_mask'), uses.getboolean('use_softmax'),
                     uses.getboolean('use_recon'), uses.getfloat('recon_beta'), uses.getboolean('reg_losses'),
                     uses.getfloat('reg_term'),
                     uses.getboolean('use_clf'), eval(str(uses.get('label_used'))), uses.getfloat('clf_alpha'))

    # REGULARIZATION
    reg = dict(config['REGULARIZATION'])

    if len(reg.keys()) > 0:
        adv_gan.set_loss(reg)

    # OPTIMIZERS
    opti_d = dict(config['D_OPTIMIZER'])

    if len(opti_d.keys()) > 0:
        adv_gan.set_optimizer_d(opti_d)

    opti_g = dict(config['G_OPTIMIZER'])

    if len(opti_g.keys()) > 0:
        adv_gan.set_optimizer_g(opti_g)

    # TRAIN
    train = config['TRAIN']

    nb_iter = train.getint('nb_iter')
    init_step = train.getint('init_step')
    n_c_iters_start = train.getint('n_c_iters_start')
    n_c_iter = train.getint('n_c_iter')
    g_iter_start = train.getint('g_iter_start')
    g_iter = train.getint('g_iter')

    adv_gan.set_training_options(nb_iter, init_step, n_c_iters_start, n_c_iter, g_iter_start, g_iter)

    # LOGS

    log = config['LOGS']

    print_method = log.get('print_method')

    if print_method == 'show_it_label':
        print_method = print_functions.show_it_label(log.get('label', 'label'))

    frequency_print = log.getint('frequency_print')
    frequency_logs = log.getint('frequency_logs')
    logs_path = log.get('logs_path')

    adv_gan.set_logs(print_method, frequency_print, frequency_logs, logs_path)

    return adv_gan
