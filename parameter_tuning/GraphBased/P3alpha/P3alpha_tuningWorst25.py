from src.Base.Evaluation.K_Fold_Evaluator import K_Fold_Evaluator_MAP
from src.Utils.load_ICM import load_ICM
from src.Utils.load_URM import load_URM
from src.Utils.ICM_preprocessing import *

URM_all = load_URM("../../../in/data_train.csv")
ICM_all = load_ICM("../../../in/data_ICM_title_abstract.csv")
from src.Data_manager.split_functions.split_train_validation_random_holdout import \
    split_train_in_two_percentage_global_sample

URMs_train = []
URMs_validation = []
ignore_users_list = []

import numpy as np

for k in range(5):
    URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_all, train_percentage=0.80)
    URMs_train.append(URM_train)
    URMs_validation.append(URM_validation)

    profile_length = np.ediff1d(URM_train.indptr)
    block_size = int(len(profile_length) * 0.25)

    start_pos = 0 * block_size
    end_pos = min(1 * block_size, len(profile_length))
    sorted_users = np.argsort(profile_length)

    users_in_group = sorted_users[start_pos:end_pos]

    users_in_group_p_len = profile_length[users_in_group]
    sorted_users = np.argsort(profile_length)

    users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
    ignore_users_list.append(sorted_users[users_not_in_group_flag])

evaluator_validation = K_Fold_Evaluator_MAP(URMs_validation, cutoff_list=[10], verbose=False,
                                            ignore_users_list=ignore_users_list)

from src.GraphBased.P3alphaRecommender import P3alphaRecommender
from bayes_opt import BayesianOptimization

p3alpha_recommenders = []

for index in range(len(URMs_train)):
    p3alpha_recommenders.append(
        P3alphaRecommender(
            URM_train=URMs_train[index],
            verbose=False
        )
    )

tuning_params = {
    "alpha": (0.1, 0.9),
    "topK": (10,600)
}

results = []


def BO_func(
        alpha,
        topK
):
    for recommender in p3alpha_recommenders:
        recommender.fit(alpha=alpha, topK=int(topK), implicit=True)

    result = evaluator_validation.evaluateRecommender(p3alpha_recommenders)
    results.append(result)
    return sum(result) / len(result)


optimizer = BayesianOptimization(
    f=BO_func,
    pbounds=tuning_params,
    verbose=5,
    random_state=5,
)

optimizer.maximize(
    init_points=20,
    n_iter=8,
)


import json

with open("logs/" + p3alpha_recommenders[0].RECOMMENDER_NAME + "_worst25_logs.json", 'w') as json_file:
    json.dump(optimizer.max, json_file)

from src.Base.Evaluation.k_fold_significance_test import compute_k_fold_significance

for recommender in p3alpha_recommenders:
    recommender.fit(alpha=optimizer.max['params']['alpha'],
                    topK=int(optimizer.max['params']['topK']), implicit=True)

result = evaluator_validation.evaluateRecommender(p3alpha_recommenders)

compute_k_fold_significance(result, *results)
