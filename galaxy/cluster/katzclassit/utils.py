# TO DO: cleanup

import math

# A hashtable of vlaues to use in the c4(n) function to apply corrections to
# estimates of std.
c4n_table = {2: 0.7978845608028654,
      3:  0.886226925452758,
      4:  0.9213177319235613,
      5:  0.9399856029866254,
      6:  0.9515328619481445,
      7:  0.9593687886998328,
      8:  0.9650304561473722,
      9:  0.9693106997139539,
      10: 0.9726592741215884,
      11: 0.9753500771452293,
      12: 0.9775593518547722,
      13: 0.9794056043142177,
      14: 0.9809714367555161,
      15: 0.9823161771626504,
      16: 0.9834835316158412,
      17: 0.9845064054718315,
      18: 0.985410043808079,
      19: 0.9862141368601935,
      20: 0.9869342675246552,
      21: 0.9875829288261562,
      22: 0.9881702533158311,
      23: 0.988704545233999,
      24: 0.9891926749585048,
      25: 0.9896403755857028,
      26: 0.9900524688409107,
      27: 0.990433039209448,
      28: 0.9907855696217323,
      29: 0.9911130482419843}

def c4(n) :
    """
    Returns the correction factor to apply to unbias estimates of standard
    deviation in low sample sizes. This implementation is based on a lookup
    table for n in [2-29] and returns 1.0 for vlaues >= 30.
    """
    if n <= 1 :
        raise ValueError("Cannot apply correction for a sample size of 1.")
    else :
        return c4n_table[n] if n < 30 else 1.0

class ContinuousValue():
    def __init__(self):
        """
        The number of values, the mean of the values, and the squared errors of
        the values.
        """
        self.num = 0
        self.mean = 0
        self.meanSq = 0

    def biased_std(self):
        """
        Returns a biased estimate of the std (i.e., the sample std)
        """
        return math.sqrt(self.meanSq / (self.num))

    def unbiased_std(self):
        """
        Returns an unbiased estimate of the std that uses Bessel's correction
        and Cochran's theorem:
            https://en.wikipedia.org/wiki/Unbiased_estimation_of_standard_deviation
        """
        if self.num < 2:
            return 0.0
        return math.sqrt(self.meanSq / (self.num - 1)) / c4(self.num)

    def __hash__(self):
        return hash("#ContinuousValue#")

    def __repr__(self):
        return repr(self.num) + repr(self.mean) + repr(self.meanSq)

    def __str__(self):
        return "%0.4f (%0.4f) [%i]" % (self.mean, self.unbiased_std(), self.num)

    def update_batch(self, data):
        """
        Calls the update function on every value in the given dataset
        """
        for x in data:
            self.update(x)

    def update(self, x):
        """
        Incrementally update the mean and squared mean error (meanSq) values in
        an efficient and practical (no precision problems) way. This uses and
        algorithm by Knuth, which I found here:
            https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        """
        self.num += 1
        delta = x - self.mean
        self.mean += delta / self.num
        self.meanSq += delta * (x - self.mean)

    def combine(self, other):
        """
        Combine two clusters of means and squared mean error (meanSq) values in
        an efficient and practical (no precision problems) way. This uses the
        parallel algorithm by Chan et al. found here:
            https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
        """
        if not isinstance(other, ContinuousValue):
            raise ValueError("Can only merge 2 continuous values.")
        delta = other.mean - self.mean
        self.meanSq = (self.meanSq + other.meanSq + delta * delta *
                       ((self.num * other.num) / (self.num + other.num)))
        self.mean = ((self.num * self.mean + other.num * other.mean) /
                     (self.num + other.num))
        self.num += other.num


def sparse_matrix_to_array_of_dicts(matrix):
    """
    Takes a sparse_coo matrix whose rows represent feature vectors of articles
    Returns a dictionary format to use on katzclassit & cobweb tests.
    """
    N = matrix.shape[0]           # number of articles
    res = [{} for i in range(N)]
    for i, j, v in zip(matrix.row, matrix.col, matrix.data):
        if v > 0:
            res[i][str(j)] = v
    return res



# Borrowed from eval.data
# TODO:

# - Train custom pipeline without normalization
# - Adapt load_articles to use this custom pipeline
# - adapt build vectors to leave out non-TF features (i.e.: published date)

import json
import pickle
from random import random, randint
from datetime import datetime

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.preprocessing import normalize
from dateutil.parser import parse

from eval.models import Article
from eval.util import progress


def load_articles(datapath, with_labels=True, as_incremental=False):
    print('Loading articles from {0}...'.format(datapath))
    with open(datapath, 'r') as file:
        data = json.load(file)

    if with_labels:
        articles, labels_true = process_labeled_articles(data)
    else:
        articles = [process_article(a) for a in data]

    print('Loaded {0} articles.'.format(len(articles)))

    if as_incremental:
        articles = split_list(articles)

    if with_labels:
        print('Expecting {0} events.'.format(len(data)))
        return articles, labels_true

    return articles


def build_kc_vectors(articles, savepath=None):
    bow_vecs, concept_vecs = [], []

    for a in progress(articles, 'Building article vectors...'):
        bow_vecs.append(a.vectors)
        concept_vecs.append(a.concept_vectors)

    print('Merging vectors...')
    vecs = hstack([bow_vecs, concept_vecs])
    print('Using {0} features.'.format(vecs.shape[1]))

    if savepath:
        with open(savepath, 'wb') as f:
            pickle.dump(vecs, f)

    return vecs


def process_labeled_articles(data):
    # Build articles and true labels.
    articles, labels_true = [], []
    for idx, cluster in enumerate(data):
        members = []
        for a in cluster['articles']:
            article = process_article(a)
            members.append(article)
        articles += members
        labels_true += [idx for i in range(len(members))]
    return articles, labels_true


def process_article(a):
    a['id'] = hash(a['title'])

    # Handle MongoDB JSON dates.
    for key in ['created_at', 'updated_at']:
        date = a[key]['$date']
        if isinstance(date, int):
            a[key] = datetime.fromtimestamp(date/1000)
        else:
            a[key] = parse(a[key]['$date'])

    return Article(**a)


def split_list(objs, n_groups=3):
    """
    Takes a list of objs and splits them into randomly-sized groups.
    This is used to simulate how articles come in different groups.
    """
    shuffled = sorted(objs, key=lambda k: random())

    sets = []
    for i in range(n_groups):
        size = len(shuffled)
        end = randint(1, (size - (n_groups - i) + 1))

        yield shuffled[:end]

        shuffled = shuffled[end:]
