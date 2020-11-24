from src.Base.Evaluation.K_Fold_Evaluator import K_Fold_Evaluator_MAP
from src.Utils.ICM_preprocessing import *
from src.Utils.load_ICM import load_ICM
from src.Utils.load_URM import load_URM

URM_all = load_URM("../../in/data_train.csv")
ICM_all = load_ICM("../../in/data_ICM_title_abstract.csv")
from src.Data_manager.split_functions.split_train_validation_random_holdout import \
    split_train_in_two_percentage_global_sample

URMs_train = []
URMs_validation = []

for k in range(5):
    URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_all, train_percentage=0.80)
    URMs_train.append(URM_train)
    URMs_validation.append(URM_validation)

evaluator_validation = K_Fold_Evaluator_MAP(URMs_validation, cutoff_list=[10], verbose=False)

ICMs_combined = []
for URM in URMs_train:
    ICMs_combined.append(combine(ICM=ICM_all, URM=URM))

from src.Hybrid.SimilarityMergedHybridRecommender import SimilarityMergedHybridRecommender
from src.GraphBased.P3alphaRecommender import P3alphaRecommender
from src.GraphBased.RP3betaCBFRecommender import RP3betaCBFRecommender

from bayes_opt import BayesianOptimization

p3alpha_recommenders = []
rp3betaCBF_recommenders = []
rp3betaCombined_recommenders = []
hybrid1Recommenders = []

for index in range(len(URMs_train)):

    p3alpha_recommenders.append(
        P3alphaRecommender(
            URM_train=URMs_train[index],
            verbose=False
        )
    )

    p3alpha_recommenders[index].fit(
        topK=int(212.8832860130684),
        alpha=0.4729294763382114,
        implicit=True
    )

    rp3betaCombined_recommenders.append(
        RP3betaCBFRecommender(
            URM_train=URMs_train[index],
            ICM_train=ICMs_combined[index],
            verbose=False
        )
    )

    rp3betaCombined_recommenders[index].fit(
        topK=int(525.3588205773788),
        alpha=0.42658191175355076,
        beta=0.2284685880641364,
        implicit=False
    )

    rp3betaCBF_recommenders.append(
        RP3betaCBFRecommender(
            URM_train=URMs_train[index],
            ICM_train=ICM_all,
            verbose=False
        )
    )

    rp3betaCBF_recommenders[index].fit(
        topK=int(58.16144182493173),
        alpha=0.26520214286626453,
        beta=0.36456352256640157,
        implicit=False
    )

    hybrid1Recommenders.append(SimilarityMergedHybridRecommender(
        URM_train=URMs_train[index],
        CFRecommender=rp3betaCombined_recommenders[index],
        CBFRecommender=p3alpha_recommenders[index],
        verbose=False
    )
    )
tuning_params = {
    "hybrid1TopK": (10, 1000),
    "hybrid1Alpha": (0.1, 0.9),
    "hybrid2TopK": (10, 1000),
    "hybrid2Alpha": (0.1, 0.9)
}

results = []
def BO_func(
        hybrid1TopK,
        hybrid1Alpha,
        hybrid2TopK,
        hybrid2Alpha
):

    recommenders = []
    for index in range(len(URMs_train)):


        hybrid1Recommenders[index].fit(
            topK=int(hybrid1TopK),
            alpha=hybrid1Alpha
        )

        recommender = SimilarityMergedHybridRecommender(
            URM_train=URMs_train[index],
            CFRecommender=hybrid1Recommenders[index],
            CBFRecommender=rp3betaCBF_recommenders[index],
            verbose=False
        )

        recommender.fit(
            topK=int(hybrid2TopK),
            alpha=hybrid2Alpha
        )

        recommenders.append(recommender)

    result = evaluator_validation.evaluateRecommender(recommenders)
    results.append(result)
    return sum(result) / len(result)


optimizer = BayesianOptimization(
    f=BO_func,
    pbounds=tuning_params,
    verbose=5,
    random_state=5,
)

optimizer.maximize(
    init_points=10,
    n_iter=18,
)

import json

with open("logs/P3alphaFeatureCombinedRP3betaRP3betaCBF_logs.json", 'w') as json_file:
    json.dump(optimizer.max, json_file)


