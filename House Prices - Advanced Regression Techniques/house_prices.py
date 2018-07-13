import preprocessing as pp
import transformers as tr
import ensemble as em
from sklearn.pipeline import Pipeline, FeatureUnion
import numpy as np
from sklearn.kernel_ridge import KernelRidge
from xgboost import XGBRegressor
import lightgbm as lgb
from sklearn.svm import SVR, LinearSVR
from sklearn.linear_model import ElasticNet, Lasso, BayesianRidge, Ridge, LassoLars
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import RobustScaler, StandardScaler
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import VarianceThreshold, SelectFromModel, SelectKBest, mutual_info_regression, RFE, f_regression
from sklearn.decomposition import PCA

def make_submission(model, X_train, y_train, X_test, filename = 'submission.csv'):
    model.fit(X_train, y_train)
    predicted = np.expm1(model.predict(X_test))
    my_submission = pd.DataFrame({'Id': ids, 'SalePrice': predicted})
    my_submission.to_csv(filename, index=False)

import warnings
def ignore_warn(*args, **kwargs):
    pass
warnings.warn = ignore_warn #ignore annoying warning (from sklearn and seaborn)

seed = 2018

train, test = pp.read_train_test()

ids = list(test.Id)

train = pp.drop_outliers(train).reset_index(drop = True)

train.drop(['Id'], axis=1, inplace = True)
test.drop(['Id'], axis=1, inplace = True)

train_y = (np.log1p(train.SalePrice)).values

train.drop(['SalePrice'], axis=1, inplace = True)

basic_pipeline = Pipeline([('convert', tr.Convert2CategoryTransformer(["MSSubClass"])),
                 ('missing', tr.HandleMissingTransformer(was_missing_features = False)),
                 ('date_related_features', tr.DateRelatedFeaturesTransformer()),    
                 ('encode_features', tr.EncodeTransformer()),
                 ])

second_pipeline = Pipeline([('features', FeatureUnion([
                         ('boolean', Pipeline([
                                 ('selector', tr.TypeSelectorTransformer('bool')),
                                 ])),
                         ('numericals', Pipeline([
                                 ('selector', tr.TypeSelectorTransformer(np.number)),
                                 
                                 ('com_log', tr.ColumnsSelectorTransformer(["LotFrontage", "LotArea"], True)),
                                 ('sem_log', tr.ColumnsSelectorTransformer(["LotFrontage", "LotArea"], False)),
                                 #('scaler', StandardScaler()),
                                 ('log', tr.LogTransformer()),
                                 ])),
                        #('categoricals', Pipeline([
                        #        ('selector', tr.TypeSelectorTransformer('object')),
                        #        ('convert', tr.Convert2CategoryTransformer()),
                        #        ('labeler', tr.StringIndexer()),
                                #('hot_encode', tr.HotEncodeTransformer()),
                        #        ]))
                 ])),
                 #('overall_features', tr.FeatureEngineeringTransformer()),
                 #('more_features', tr.MoreFeaturesTransformer()),
                 #('neighbourhood_features', tr.NeighbourhoodRelatedFeaturesTransformer()),
                 ])

train_X = basic_pipeline.fit_transform(train, train_y)
test_X = basic_pipeline.fit_transform(test)

train_X = second_pipeline.fit_transform(train_X, train_y)
test_X = second_pipeline.fit_transform(test_X)

third_pipeline = Pipeline([('scaler', RobustScaler()),
                           ('low_variance', VarianceThreshold(0.98 * (1 - 0.98))),
                           ('fu', FeatureUnion([
                                   #('pca', PCA(n_components=10)),
                                   #('kbest', SelectKBest(mutual_info_regression, k=110)),
                                   ('reduce_dim_lasso', SelectFromModel(Lasso(alpha=0.0004, random_state = seed))),
                                   #('reduce_dim_rfe', RFE(Lasso(alpha=0.0004), 115, step=10))
                                   #('reduce_dim_rf', SelectFromModel(RandomForestRegressor(n_estimators = 500, 
                                   #                                                     max_features = 0.4, 
                                   #                                                     min_samples_split = 4,
                                   #                                                     random_state = seed), threshold = "mean")),
                                   ])),
                           ])

train_X_reduced = third_pipeline.fit_transform(train_X, train_y)
test_X_reduced = third_pipeline.transform(test_X)

X_train, X_test, y_train, y_test = train_test_split(train_X_reduced, train_y, test_size=0.2)

##################

np.set_printoptions(precision = 4)
pd.set_option('precision', 4)

model_ridge = Ridge(alpha=12.0, random_state=seed)
model_KRR = KernelRidge(alpha=0.2, kernel='polynomial', degree=2, coef0=2.0, gamma=0.0032)
model_svr = SVR(C=44.73, epsilon = 0.0774, gamma = 0.0004, kernel = 'rbf')
model_byr = BayesianRidge()
model_ENet = ElasticNet(alpha=0.0001, l1_ratio=0.551, random_state=seed, max_iter = 10000)
model_lasso = Lasso(alpha=0.0004, random_state = seed)
model_lsvr = LinearSVR(C=0.525, epsilon= 0.04, random_state=seed)
model_lasso_lars = LassoLars(alpha=1.22e-05)

model_rforest = RandomForestRegressor(n_estimators = 300, max_features = 0.4, 
                                      min_samples_split = 4,
                                      random_state=seed)

model_GBoost = GradientBoostingRegressor(n_estimators=1000, learning_rate=0.03,
                                   max_depth=3, max_features=0.4,
                                   min_samples_leaf=20, min_samples_split=10, 
                                   loss='huber', random_state = seed)

model_xgb = XGBRegressor(colsample_bytree=0.35, gamma=0.027, 
                             learning_rate=0.03, max_depth=4, 
                             min_child_weight=1.7817, n_estimators=1000,
                             reg_alpha=0.43, reg_lambda=0.88,
                             subsample=0.5213, silent=1,
                             random_state = seed)

model_lgb = lgb.LGBMRegressor(objective='regression',num_leaves=10,
                              learning_rate=0.03, n_estimators=720,
                              max_bin = 55, bagging_fraction = 0.8,
                              bagging_freq = 5, feature_fraction = 0.2319,
                              feature_fraction_seed=9, bagging_seed=9,
                              min_data_in_leaf =6, min_sum_hessian_in_leaf = 11)



#Linear Models
linear_models = []
linear_models.append(("lasso", model_lasso))
linear_models.append(("ridge", model_ridge))
linear_models.append(("svr", model_svr))
linear_models.append(("ENet", model_ENet))
linear_models.append(("KRR", model_KRR))
linear_models.append(("byr", model_byr))
linear_models.append(("lsvr", model_lsvr))
#linear_models.append(("lasso_lars", model_lasso_lars))

tree_models = []
tree_models.append(("rforest", model_rforest))
tree_models.append(("GBoost", model_GBoost))
tree_models.append(("xgb", model_xgb))
tree_models.append(("lgb", model_lgb))

linear_results = pp.get_cross_validate(linear_models, train_X_reduced, train_y.ravel(), 
                                       folds = 10, repetitions = 3, seed = seed, train_score = False, jobs = 2)
print(linear_results)


tree_results = pp.get_cross_validate(tree_models, train_X_reduced, train_y.ravel(), 
                                     folds = 10, seed = seed, train_score = False)
print(tree_results)

averaged_models = em.AveragingModels(models = [model_lgb, model_KRR, model_svr])
stacked_averaged_models = em.StackingAveragedModels(base_models = [model_svr, model_lgb], meta_model = model_KRR)
averaged_plus = em.AveragingModels(models = [averaged_models, model_GBoost, model_xgb], weights = [0.7, 0.2, 0.1])
averaged_plus_plus = em.AveragingModels(models = [stacked_averaged_models, model_GBoost, model_xgb], weights = [0.7, 0.2, 0.1])

avg_full = em.AveragingModels(models = [em.AveragingModels(models = [model_KRR, model_ridge, model_lsvr]), 
                                        em.AveragingModels(models = [model_lgb, model_GBoost, model_xgb])])

ensemble_models = []
ensemble_models.append(("averaged", averaged_models))
ensemble_models.append(("stacked", stacked_averaged_models))
ensemble_models.append(("averaged_plus", averaged_plus))
ensemble_models.append(("averaged_plus_plus", averaged_plus_plus))
ensemble_models.append(("averaged_full", avg_full))

ensemble_results = pp.get_cross_validate(ensemble_models, train_X_reduced, train_y.ravel(), 
                                     folds = 10, repetitions = 3, seed = seed, train_score = False)
print(ensemble_results)

make_submission(averaged_models, train_X_reduced, train_y, test_X_reduced, filename = 'submission_avg.csv')


import cv_lab as cvl
hyperparameters = {'alpha':np.linspace(0.2,1.0,20)}
hpg = cvl.HousePricesGridCV(KernelRidge(kernel='polynomial', degree=2, coef0=2.0, gamma=0.0032),
                            hyperparameters = hyperparameters, n_folds = 10, seed = seed)
hpg.fit(train_X_reduced, train_y.ravel())
hpg.get_best_results()
hpg.plot_scores()