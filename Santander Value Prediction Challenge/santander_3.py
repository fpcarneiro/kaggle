import preprocessing as pp
import ensemble as em
import transformers as tf
import regressors as reg
import cv_lab as cvl
import feature_selection as fs

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.decomposition import PCA

from sklearn.preprocessing import RobustScaler, FunctionTransformer, StandardScaler
from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_regression
from sklearn.feature_selection import SelectPercentile, SelectFromModel, mutual_info_regression
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import BayesianRidge, Lasso, Ridge
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.model_selection import train_test_split

import lightgbm as lgb

from xgboost import XGBRegressor

import warnings
def ignore_warn(*args, **kwargs):
    pass
warnings.warn = ignore_warn

def get_rfc():
    return RandomForestClassifier(
        n_estimators=10,
        max_features=0.5,
        max_depth=None,
        max_leaf_nodes=270,
        min_impurity_decrease=0.0001,
        random_state=123,
        n_jobs=-1
    )
    
xgb_params = {
        'n_estimators': 1500,
        'objective': 'reg:linear',
        'booster': 'gbtree',
        'learning_rate': 0.02,
        'max_depth': 22,
        'min_child_weight': 57,
        'gamma' : 1.45,
        'alpha': 0.0,
        'lambda': 0.0,
        'subsample': 0.67,
        'colsample_bytree': 0.054,
        'colsample_bylevel': 0.50,
        'n_jobs': -1,
        'random_state': 456
    }
    
fit_params = {
        'early_stopping_rounds': 15,
        'eval_metric': 'rmse',
        'verbose': False
    }

import matplotlib.pyplot as plt
plt.spy(train)

train, test = pp.read_train_test(train_file = 'train.csv', test_file = 'test.csv')

#train_sparse = train.replace(0, np.nan).to_sparse()
#test_sparse = test.replace(0, np.nan).to_sparse()

#train_X_sparse = train_sparse.drop(['ID','target'], axis=1)
#train_y_sparse = (np.log1p(train_sparse.target)).values

ids = list(test.ID)

train_X = train.drop(['ID','target'], axis=1)
train_y = (np.log1p(train.target)).values

test_X = test.drop(['ID'], axis=1)

pipe = Pipeline(
        [
            ('vt', VarianceThreshold(threshold=0.0)),
            ('ut', tf.UniqueTransformer()),
            #('fu', FeatureUnion(
             #       [
              #          ('pca', PCA(n_components=100)),
               #         ('ct-2', tf.ClassifierTransformer(get_rfc(), n_classes=2, cv=5)),
                #        ('ct-3', tf.ClassifierTransformer(get_rfc(), n_classes=3, cv=5)),
                 #       ('ct-4', tf.ClassifierTransformer(get_rfc(), n_classes=4, cv=5)),
                  #      ('ct-5', tf.ClassifierTransformer(get_rfc(), n_classes=5, cv=5)),
                   #     ('st', tf.StatsTransformer(stat_funs=tf.get_stat_funs()))
                    #]
                #)
            #),
            #('xgb-cv', reg.XGBRegressorCV(
            #        xgb_params=xgb_params,
            #        fit_params=fit_params,
            #        cv=10
            #    )
            #)
        ]
    )

pipe.fit(train_X, train_y)
print(pipe.named_steps['xgb-cv'].cv_scores_)
print(pipe.named_steps['xgb-cv'].cv_score_)

train_X_reduced = pipe.transform(train_X)
test_X_reduced = pipe.transform(test_X)

print(train_X_reduced.shape)
print(test_X_reduced.shape)

train_set_X, test_set_X, train_set_y, test_set_y = train_test_split(train_X_reduced, train_y, test_size=0.1)

train_set_X.shape


rf = RandomForestClassifier()




tree_models = []
models = []
for s in [27,22,300,401,7]:
    model_lgb = lgb.LGBMRegressor(boosting_type = 'gbdt',
                              num_leaves = 200,
                              max_depth = -1,
                              learning_rate = 0.01,
                              n_estimators = 295,
                              #subsample_for_bin = 50000,
                              objective='regression',
                              #class_weight = None,
                              #min_split_gain = 0.
                              min_child_weight = 10,
                              #min_child_samples = 20,
                              subsample = 1.,
                              subsample_freq = 0,
                              colsample_bytree = 1.,
                              reg_alpha = 0.3,
                              reg_lambda = 0.1,
                              random_state = s,
                              n_jobs = -1,
                              silent = False,
                              metric="rmse",
                              
                              num_boost_round = 295,
                              bagging_fraction = 0.5,
                              bagging_frequency = 4,
                              feature_fraction = 0.5,
                              #early_stopping_rounds=100
                              verbose_eval=10,
                              random_seed = s
                              )
    tree_models.append(("lgb_" + str(s), model_lgb))
    #tree_models.append(("rf", model_rforest))
    #tree_models.append(("xgb", model_xgb))
    models.append(model_lgb)

tree_results = pp.get_cross_validate(tree_models, train_set_X, train_set_y, 
                                     folds = 10, seed = 2018, train_score = False, jobs = -1)
print(tree_results)

model_lgb.fit(train_set_X, train_set_y)
predicted = model_lgb.predict(test_set_X)
score_val = cvl.score_sq(test_set_y, predicted)

averaged_models = em.AveragingModels(models = models)

ensemble_models = []
ensemble_models.append(("averaged", averaged_models))

cross_val_table_avg = pp.get_validation_scores(ensemble_models, train_X_reduced, train_y, 5)
print(cross_val_table_avg)

pp.make_submission(averaged_models, train_X_reduced, train_y, 
                   test_X_reduced, ids, filename = 'submission.csv')


lgbm_params =  {
    'task': 'train',
    'boosting_type': 'gbdt',
    'objective': 'regression',
    'metric': 'rmse',
    "learning_rate": 0.01,
    "num_leaves": 200,
    "feature_fraction": 0.50,
    "bagging_fraction": 0.50,
    'bagging_freq': 4,
    "max_depth": -1,
    "reg_alpha": 0.3,
    "reg_lambda": 0.1,
    #"min_split_gain":0.2,
    "min_child_weight":10,
    'zero_as_missing':True
}



model_lgb = lgb.LGBMRegressor(params = lgbm_params)

lgb_train = lgb.Dataset(train_X_reduced, train_y, feature_name = "auto")


lgb_cv = lgb.cv(
    params = lgbm_params,
    train_set = lgb_train,
    num_boost_round=2500,
    stratified=False,
    nfold = 5,
    verbose_eval=50,
    seed = 23,
    early_stopping_rounds=75)

results = pd.DataFrame(columns = ["Rounds","Score","STDV", "LB", "Parameters"])
optimal_rounds = np.argmin(lgb_cv['rmse-mean'])
best_cv_score = min(lgb_cv['rmse-mean'])

print("\nOptimal Round: {}\nOptimal Score: {} + {}".format(
    optimal_rounds,best_cv_score,lgb_cv['rmse-stdv'][optimal_rounds]))

results = results.append({"Rounds": optimal_rounds,
                          "Score": best_cv_score,
                          "STDV": lgb_cv['rmse-stdv'][optimal_rounds],
                          "LB": None,
                          "Parameters": lgbm_params}, ignore_index=True)

pd.set_option('max_colwidth', 800)
display(results.sort_values(by="Score",ascending = True))

learning_rates = [0.012,0.008]
for param in learning_rates:
    print("Learning Rate: ", param)
    lgbm_params["learning_rate"] = param
    # Find Optimal Parameters / Boosting Rounds
    lgb_cv = lgb.cv(
        params = lgbm_params,
        train_set = lgb_train,
        num_boost_round=10000,
        stratified=False,
        nfold = 5,
        verbose_eval=10,
        seed = 23,
        early_stopping_rounds=100)

optimal_rounds = np.argmin(lgb_cv['rmse-mean'])
best_cv_score = min(lgb_cv['rmse-mean'])

print("Optimal Round: {}\nOptimal Score: {} + {}".format(
        optimal_rounds,best_cv_score,lgb_cv['rmse-stdv'][optimal_rounds]))
print("###########################################################################################")

results = results.append({"Rounds": optimal_rounds,
                              "Score": best_cv_score,
                              "STDV": lgb_cv['rmse-stdv'][optimal_rounds],
                              "LB": None,
                              "Parameters": lgbm_params}, ignore_index=True)


pd.set_option('max_colwidth', 800)
display(results.sort_values(by="Score",ascending = True))


# Best Parameters
final_model_params = results.iloc[results["Score"].idxmin(),:]["Parameters"]
optimal_rounds = results.iloc[results["Score"].idxmin(),:]["Rounds"]
print("Parameters for Final Models:\n",final_model_params)
print("Score: {} +/- {}".format(results.iloc[results["Score"].idxmin(),:]["Score"],results.iloc[results["Score"].idxmin(),:]["STDV"]))
print("Rounds: ", optimal_rounds)

multi_seed_pred = dict()
all_feature_importance_df  = pd.DataFrame()


all_seeds = [27,22,300,401]
for seeds_x in all_seeds:
    print("Seed: ", seeds_x,)
    # Go Go Go
    final_model_params["seed"] = seeds_x
    lgb_reg = lgb.train(
        final_model_params,
        lgb_train,
        num_boost_round = int(optimal_rounds + 1),
        verbose_eval=10)

    multi_seed_pred[seeds_x] =  list(lgb_reg.predict(test_X))
    
    del lgb_reg

cols = all_feature_importance_df[["feature", "importance"]].groupby("feature").mean().sort_values(
    by="importance", ascending=False)[:50].index
best_features = all_feature_importance_df.loc[all_feature_importance_df.feature.isin(cols)]


# To DataFrame
sub_preds = pd.DataFrame.from_dict(multi_seed_pred).replace(0,0.000001)

for i in range(4):
    score_val = cvl.score_sq(test_set_y, sub_preds.iloc[:,i])
    print(score_val)
ms = sub_preds.mean(axis=1).rename("target")
score_val = cvl.score_sq(test_set_y, ms)
print(score_val)

mean_sub = np.expm1(sub_preds.mean(axis=1).rename("target"))
mean_sub.index = ids

# Submit
mean_sub.to_csv('mean_sub_ep{}_sc{}.csv'.format(optimal_rounds,round(best_cv_score,5))
            ,index = True, header=True)
mean_sub.head()




from sklearn.decomposition import PCA, TruncatedSVD, FastICA
N_COMP = 20

pca = PCA(n_components=N_COMP, random_state=17)
pca_results_train = pca.fit_transform(train_X_reduced)
pca_results_test = pca.transform(test_X_reduced)

tsvd = TruncatedSVD(n_components=N_COMP, random_state=17)
tsvd_results_train = tsvd.fit_transform(train_X_reduced)
tsvd_results_test = tsvd.transform(test_X_reduced)




for i_class in range(3):
    if i_class + 1 == 3:
        y_labels[a >= y_us[i_class * step]] = i_class
    else:
        y_labels[
            np.logical_and(
                a >= y_us[i_class * step],
                a < y_us[(i_class + 1) * step]
            )
        ] = i_class
print (y_labels)