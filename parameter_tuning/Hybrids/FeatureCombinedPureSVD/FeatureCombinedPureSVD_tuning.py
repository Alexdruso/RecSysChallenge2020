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

for k in range(5):
    URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_all, train_percentage=0.80)
    URMs_train.append(URM_train)
    URMs_validation.append(URM_validation)

evaluator_validation = K_Fold_Evaluator_MAP(URMs_validation, cutoff_list=[10], verbose=False)

#binarize_ICM(ICM_all)
ICMs_combined = []
for URM in URMs_train:
    ICMs_combined.append(combine(ICM=ICM_all, URM=URM))

from src.MatrixFactorization.PureSVDRecommender import PureSVDRecommender

from bayes_opt import BayesianOptimization

pureSVD_recommenders = []

for index in range(len(URMs_train)):
    pureSVD_recommenders.append(
        PureSVDRecommender(
            URM_train=ICMs_combined[index].T,
            verbose=False
        )
    )

tuning_params = {
    "num_factors":(10, 800),
    "n_iter": (1, 10)
}

results = []


def BO_func(
        num_factors,
        n_iter
):
    for recommender in pureSVD_recommenders:
        recommender.fit(num_factors=int(num_factors), random_seed=1, n_iter=int(n_iter))

    result = evaluator_validation.evaluateRecommender(pureSVD_recommenders)
    results.append(result)
    return sum(result) / len(result)


optimizer = BayesianOptimization(
    f=BO_func,
    pbounds=tuning_params,
    verbose=5,
    random_state=5,
)

optimizer.maximize(
    init_points=50,
    n_iter=20,
)


import json

with open("logs/FeatureCombined" + pureSVD_recommenders[0].RECOMMENDER_NAME + "_logs.json", 'w') as json_file:
    json.dump(optimizer.max, json_file)

