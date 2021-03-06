from src.Base.Evaluation.Evaluator import EvaluatorHoldout
from src.Utils.load_ICM import load_ICM
from src.Utils.load_URM import load_URM
from src.Utils.ICM_preprocessing import *

URM_all = load_URM("../../../in/data_train.csv")
ICM_all = load_ICM("../../../in/data_ICM_title_abstract.csv")
from src.Data_manager.split_functions.split_train_validation_random_holdout import \
    split_train_in_two_percentage_global_sample

URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_all, train_percentage=0.80)

evaluator_validation = EvaluatorHoldout(URM_validation, cutoff_list=[10], verbose=False)

from src.EASE_R.EASE_R_CBF_Recommender import EASE_R_CBF_Recommender
from bayes_opt import BayesianOptimization

binarize_ICM(ICM_all)

ICM_all = combine(ICM_all, URM_train)

easerCBF_recommender = EASE_R_CBF_Recommender(URM_train=URM_train, ICM_train=ICM_all, verbose=False)

tuning_params = {
    "topK": (10, 150),
    "l2_norm": (1e2, 1e5)
}


def BO_func(
        topK,
        l2_norm
):
    easerCBF_recommender.fit(topK=int(topK), l2_norm=l2_norm)
    result_dict, _ = evaluator_validation.evaluateRecommender(easerCBF_recommender)

    return result_dict[10]["MAP"]


optimizer = BayesianOptimization(
    f=BO_func,
    pbounds=tuning_params,
    verbose=5,
    random_state=5,
)

optimizer.maximize(
    init_points=5,
    n_iter=3,
)

import json

with open("logs/FeatureCombined" + easerCBF_recommender.RECOMMENDER_NAME + "_logs.json", 'w') as json_file:
    json.dump(optimizer.max, json_file)
